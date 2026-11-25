import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.admin.router import purge_user
from app.db import database
from app.models import LoginSession, User
from app.schemas import AdminCreate, AdminEdit, DeleteConfirm
from app.security import audit, csrf, hasher, owner_user, public_user, rate_limit

router = APIRouter(prefix="/admin/admins", tags=["administracion"], dependencies=[Depends(owner_user)])


def target(db, admin_id, actor):
    u = db.scalar(select(User).where(User.id == admin_id).with_for_update())
    if not u or u.role != "admin":
        raise HTTPException(404, "Usuario no encontrado.")
    if u.owner or u.id == actor.id:
        raise HTTPException(400, "La cuenta del administrador principal no se modifica desde aquí.")
    return u


@router.post("", status_code=201, dependencies=[Depends(csrf)])
def create(data: AdminCreate, actor: User = Depends(owner_user), db: Session = Depends(database, scope="function")):
    rate_limit("admin-create", str(actor.id), 10, 900)
    if db.scalar(select(User.id).where(User.username == data.username)):
        raise HTTPException(409, "Ese usuario ya existe.")
    u = User(username=data.username, name=data.name, password_hash=hasher.hash(data.password), role="admin",
             can_generate=True, owner=False, permissions=sorted(set(data.permissions)))
    db.add(u)
    db.flush()
    audit(db, actor, "admin_created", str(u.id), username=u.username, permissions=u.permissions)
    return public_user(u)


@router.patch("/{admin_id}", dependencies=[Depends(csrf)])
def edit(admin_id: uuid.UUID, data: AdminEdit, actor: User = Depends(owner_user), db: Session = Depends(database, scope="function")):
    u = target(db, admin_id, actor)
    u.name, u.active, u.permissions = data.name, data.active, sorted(set(data.permissions))
    if data.password:
        rate_limit("admin-password", str(actor.id), 10, 900)
        u.password_hash = hasher.hash(data.password)
    if data.password or not u.active:
        db.execute(delete(LoginSession).where(LoginSession.user_id == u.id))
    audit(db, actor, "admin_edited", str(u.id), permissions=u.permissions, active=u.active, password=bool(data.password))
    return public_user(u)


@router.delete("/{admin_id}", dependencies=[Depends(csrf)])
def remove(admin_id: uuid.UUID, data: DeleteConfirm, tasks: BackgroundTasks, actor: User = Depends(owner_user),
           db: Session = Depends(database, scope="function")):
    rate_limit("admin-delete-user", str(actor.id), 10, 900)
    u = target(db, admin_id, actor)
    if data.confirm != u.username:
        raise HTTPException(400, "Escribe el usuario exacto para confirmar.")
    return purge_user(db, u, actor, tasks)
