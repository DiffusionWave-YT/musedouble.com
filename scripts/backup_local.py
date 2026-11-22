import os
from pathlib import Path
import subprocess
import hashlib
import json
import tarfile
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def pg_environment(url, dbname=None):
    p=urlsplit(url.replace("postgresql+psycopg://","postgresql://",1))
    return dict(os.environ,PGHOST=p.hostname,PGPORT=str(p.port or 5432),PGUSER=unquote(p.username),
                PGPASSWORD=unquote(p.password),PGDATABASE=dbname or p.path.lstrip("/"))


def backup():
    config=dotenv_values(ROOT/".env")
    dest=ROOT/"storage/backups"/("postgres-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]+".dump")
    dest.parent.mkdir(exist_ok=True,parents=True)
    binary=Path(os.environ.get("MUSE_PG_BIN","C:/Program Files/PostgreSQL/18/bin"))/"pg_dump.exe"
    result=subprocess.run([str(binary),"--format=custom","--no-owner","--file",str(dest)],
        env=pg_environment(config["MUSE_MIGRATION_DATABASE_URL"]),capture_output=True,timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    if result.returncode:
        raise SystemExit("No se pudo crear el respaldo PostgreSQL.")
    bundle=dest.with_suffix(".objects.tar.gz")
    manifest={}
    objects=ROOT/"storage/objects"
    with tarfile.open(bundle,"w:gz") as archive:
        for folder in ("outputs","uploads","workflows"):
            if not (objects/folder).exists():
                continue
            for path in sorted((objects/folder).rglob("*")):
                if path.is_file() and not path.is_symlink() and not path.name.endswith(".tmp"):
                    key=path.relative_to(objects).as_posix()
                    archive.add(path,arcname=key,recursive=False)
                    manifest[key]=hashlib.sha256(path.read_bytes()).hexdigest()
    dest.with_suffix(".objects.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("Respaldo privado: "+str(dest.relative_to(ROOT)))
    return dest


if __name__=="__main__":
    backup()
