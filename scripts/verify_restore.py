import json
import os
from pathlib import Path
import subprocess
import uuid
import tarfile
import hashlib
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from backup_local import ROOT, backup, pg_environment

config=dotenv_values(ROOT/".env")
auth=json.loads((ROOT/"storage/runtime/local-database.json").read_text())
dest=backup()
dbname="muse_restore_test_"+uuid.uuid4().hex
assert dbname.startswith("muse_restore_test_") and len(dbname)==50
bootstrap=dict(host="127.0.0.1",port=auth["port"],dbname="postgres",user="musedouble_bootstrap",password=auth["bootstrap_password"])
with psycopg.connect(**bootstrap,autocommit=True) as db:
    db.execute(sql.SQL("CREATE DATABASE {} OWNER musedouble_owner").format(sql.Identifier(dbname)))
try:
    binary=Path(os.environ.get("MUSE_PG_BIN","C:/Program Files/PostgreSQL/18/bin"))/"pg_restore.exe"
    r=subprocess.run([str(binary),"--no-owner","--no-acl","--exit-on-error","--dbname",dbname,str(dest)],
                     env=pg_environment(config["MUSE_MIGRATION_DATABASE_URL"],dbname),capture_output=True,timeout=60,
                     creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    if r.returncode:
        raise SystemExit("Falló la restauración de prueba.")
    original=pg_environment(config["MUSE_MIGRATION_DATABASE_URL"])
    common=dict(host=original["PGHOST"],port=original["PGPORT"],user=original["PGUSER"],password=original["PGPASSWORD"])
    counts={}
    object_restore=ROOT/"storage/restore-tests"/dbname
    object_restore.mkdir(parents=True)
    with tarfile.open(dest.with_suffix(".objects.tar.gz"),"r:gz") as archive:
        archive.extractall(object_restore,filter="data")
    manifest=json.loads(dest.with_suffix(".objects.json").read_text())
    with psycopg.connect(**common,dbname=original["PGDATABASE"]) as src, psycopg.connect(**common,dbname=dbname) as restored:
        for table in ["users","models","workflows","jobs","job_outputs","credit_ledger"]:
            query=sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            a=src.execute(query).fetchone()[0];b=restored.execute(query).fetchone()[0]
            assert a==b,(table,a,b)
            counts[table]=a
        output_rows=restored.execute("SELECT object_key,size FROM job_outputs").fetchall()
        for key,size in output_rows:
            path=(object_restore/key).resolve()
            assert path.is_relative_to(object_restore.resolve()) and path.is_file()
            raw=path.read_bytes()
            assert len(raw)==size and hashlib.sha256(raw).hexdigest()==manifest[key]
    report={"restored_and_verified":True,"backup":str(dest.relative_to(ROOT)),"counts":counts,
            "restored_originals_verified":len(output_rows),"object_bundle":str(dest.with_suffix('.objects.tar.gz').relative_to(ROOT)),
            "private_keys_required":"Conservar .env y local-database.json por separado, bajo acceso privado."}
    (ROOT/"storage/restore-verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Restauración verificada en una base temporal; tablas y cantidades coinciden.")
finally:
    with psycopg.connect(**bootstrap,autocommit=True) as db:
        db.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(dbname)))
