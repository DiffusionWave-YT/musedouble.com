import argparse
import getpass
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
from app.security import hasher

parser=argparse.ArgumentParser()
parser.add_argument("--username", default="jhon")
args=parser.parse_args()
if not re.fullmatch(r"[a-z0-9_]{3,40}",args.username):
    raise SystemExit("Usuario no válido.")
with SessionLocal.begin() as db:
    if db.scalar(select(User.id).where(User.username==args.username)):
        raise SystemExit("Esa cuenta ya existe; no se modifica su contraseña ni su rol.")
    password=getpass.getpass("Contraseña nueva (mínimo 10 caracteres): ")
    confirm=getpass.getpass("Repetir contraseña: ")
    if password!=confirm or not 10<=len(password)<=128:
        raise SystemExit("Las contraseñas deben coincidir y tener entre 10 y 128 caracteres.")
    db.add(User(username=args.username,name=args.username,password_hash=hasher.hash(password),role="admin",can_generate=True))
print("Administrador creado. Los créditos se asignan desde el panel.")
