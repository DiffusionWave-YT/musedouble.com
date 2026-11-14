"""Create an isolated loopback-only PostgreSQL cluster. Never touches existing services."""
import json
import os
from pathlib import Path
import secrets
import subprocess
from cryptography.fernet import Fernet
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
storage = ROOT / "storage"
runtime = storage / "runtime"
runtime.mkdir(parents=True, exist_ok=True)
env_file = ROOT / ".env"
flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
pg_bin = Path(os.environ.get("MUSE_PG_BIN", "C:/Program Files/PostgreSQL/18/bin"))
cluster = runtime / "postgres"
secrets_file = runtime / "local-database.json"


def run(args):
    # PostgreSQL children inherit file handles on Windows; never give a daemon a pipe.
    with (runtime / "setup.log").open("a", encoding="utf-8") as output:
        p = subprocess.run([str(a) for a in args], stdout=output, stderr=output, creationflags=flags, timeout=60)
    if p.returncode:
        raise SystemExit("No se pudo preparar PostgreSQL local. Revisa storage/runtime/setup.log.")


def main():
    if not secrets_file.exists():
        if cluster.exists() or env_file.exists():
            raise SystemExit("Hay configuración existente. No se sobrescribe automáticamente.")
        auth = {"owner_password": secrets.token_urlsafe(32), "app_password": secrets.token_urlsafe(32),
                "bootstrap_password": secrets.token_urlsafe(32), "port": 55432}
        secrets_file.write_text(json.dumps(auth), encoding="utf-8")
    auth = json.loads(secrets_file.read_text())
    if not (cluster / "PG_VERSION").exists():
        pwfile = runtime / "initdb-password.tmp"
        pwfile.write_text(auth["bootstrap_password"], encoding="utf-8")
        try:
            run([pg_bin / "initdb.exe", "-D", cluster, "-U", "musedouble_bootstrap", "-A", "scram-sha-256",
                 "--pwfile=" + str(pwfile), "--encoding=UTF8", "--locale=C"])
        finally:
            pwfile.unlink(missing_ok=True)
        with (cluster / "postgresql.conf").open("a") as f:
            f.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\nmax_connections = 60\nshared_buffers = '64MB'\n")
    status = subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(cluster), "status"], capture_output=True, creationflags=flags)
    if status.returncode:
        run([pg_bin / "pg_ctl.exe", "-D", cluster, "-l", runtime / "postgres.log", "-w", "start"])
    conn_args = dict(host="127.0.0.1", port=auth["port"], dbname="postgres", user="musedouble_bootstrap", password=auth["bootstrap_password"])
    with psycopg.connect(**conn_args, autocommit=True) as db:
        for role, password in [("musedouble_owner", auth["owner_password"]), ("musedouble_app", auth["app_password"])]:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                db.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(sql.Identifier(role), sql.Literal(password)))
        if not db.execute("SELECT 1 FROM pg_database WHERE datname='musedouble_local'").fetchone():
            db.execute("CREATE DATABASE musedouble_local OWNER musedouble_owner")
            db.execute("REVOKE ALL ON DATABASE musedouble_local FROM PUBLIC")
            db.execute("GRANT CONNECT ON DATABASE musedouble_local TO musedouble_owner,musedouble_app")
    if not env_file.exists():
        hosts = ["127.0.0.1", "localhost"]
        lines = ["MUSE_ENV=local", f"MUSE_DATABASE_URL=postgresql+psycopg://musedouble_app:{auth['app_password']}@127.0.0.1:55432/musedouble_local",
                 f"MUSE_MIGRATION_DATABASE_URL=postgresql+psycopg://musedouble_owner:{auth['owner_password']}@127.0.0.1:55432/musedouble_local",
                 "MUSE_ENCRYPTION_KEY=" + Fernet.generate_key().decode(), "MUSE_SIGNING_KEY=" + secrets.token_hex(32),
                 "MUSE_ALLOWED_GPU_HOSTS=" + ",".join(hosts), "MUSE_WEB_ORIGIN=http://127.0.0.1:3001",
                 "MUSE_API_ORIGIN=http://127.0.0.1:8010", "MUSE_OBJECT_ORIGIN=http://127.0.0.1:9011", "MUSE_COOKIE_SECURE=false"]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PostgreSQL local listo en 127.0.0.1:55432. Configuración privada conservada en .env.")


if __name__ == "__main__":
    main()
