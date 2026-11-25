import secrets
import uuid
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import database
from app.models import RedeemCode, Redemption, User, now
from app.schemas import CodeInput, CodeUpdate
from app.security import admin_user, audit, csrf, section_gate

router = APIRouter(prefix="/admin/codes", tags=["administracion"], dependencies=[Depends(section_gate)])

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generated():
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))


def aware(value):
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def state(row):
    if not row.active:
        return "disabled"
    if row.expires_at and row.expires_at <= now():
        return "expired"
    if row.uses >= row.max_uses:
        return "exhausted"
    return "active"


def public(row):
    return {"id": str(row.id), "code": row.code, "credits": row.credits, "max_uses": row.max_uses, "uses": row.uses,
            "expires_at": row.expires_at, "active": row.active, "note": row.note, "created_at": row.created_at,
            "state": state(row)}


def future(value):
    value = aware(value)
    if value is not None and value <= now():
        raise HTTPException(400, "La expiración debe ser una fecha futura.")
    return value


@router.get("")
def codes(db: Session = Depends(database, scope="function")):
    return {"items": [public(r) for r in db.scalars(select(RedeemCode).order_by(RedeemCode.created_at.desc()))]}


@router.post("", status_code=201, dependencies=[Depends(csrf)])
def create(data: CodeInput, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    expires = future(data.expires_at)
    code = data.code.upper() if data.code else generated()
    if db.scalar(select(RedeemCode.id).where(RedeemCode.code == code)):
        raise HTTPException(409, "Ya existe un código igual.")
    row = RedeemCode(code=code, credits=data.credits, max_uses=data.max_uses, expires_at=expires, note=data.note)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Ya existe un código igual.") from None
    audit(db, actor, "code_created", str(row.id), credits=data.credits, max_uses=data.max_uses)
    return public(row)


@router.patch("/{code_id}", dependencies=[Depends(csrf)])
def update(code_id: uuid.UUID, data: CodeUpdate, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    row = db.scalar(select(RedeemCode).where(RedeemCode.id == code_id).with_for_update())
    if not row:
        raise HTTPException(404, "Código no encontrado.")
    if data.max_uses < row.uses:
        raise HTTPException(400, "El máximo de usos no puede ser menor a los usos ya realizados.")
    expires = aware(data.expires_at)
    if expires is not None and expires != aware(row.expires_at) and expires <= now():
        raise HTTPException(400, "La expiración debe ser una fecha futura.")
    row.active, row.max_uses, row.expires_at, row.note = data.active, data.max_uses, expires, data.note
    audit(db, actor, "code_updated", str(row.id), active=data.active, max_uses=data.max_uses)
    return public(row)


@router.delete("/{code_id}", dependencies=[Depends(csrf)])
def remove(code_id: uuid.UUID, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    row = db.scalar(select(RedeemCode).where(RedeemCode.id == code_id).with_for_update())
    if not row:
        raise HTTPException(404, "Código no encontrado.")
    db.delete(row)
    audit(db, actor, "code_deleted", str(code_id), uses=row.uses)
    return {"ok": True}


@router.get("/{code_id}/redemptions")
def redemptions(code_id: uuid.UUID, db: Session = Depends(database, scope="function")):
    if not db.get(RedeemCode, code_id):
        raise HTTPException(404, "Código no encontrado.")
    rows = db.execute(select(Redemption.created_at, User.id, User.name, User.username).join(User, User.id == Redemption.user_id)
                      .where(Redemption.code_id == code_id).order_by(Redemption.created_at.desc())).all()
    return {"items": [{"user_id": str(r.id), "name": r.name, "username": r.username, "created_at": r.created_at} for r in rows]}
