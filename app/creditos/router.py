from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.creditos.service import balance
from app.db import database
from app.models import CreditEntry, RedeemCode, Redemption, User, now
from app.schemas import RedeemInput
from app.security import audit, csrf, current_user, rate_limit

router = APIRouter(tags=["creditos"])


@router.post("/credits/redeem", dependencies=[Depends(csrf)])
def redeem(data: RedeemInput, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rate_limit("redeem", str(user.id), 10, 900)
    if not user.email_verified:
        raise HTTPException(403, "Confirma tu correo para usar el estudio.")
    code = data.code.strip().upper()
    row = db.scalar(select(RedeemCode).where(RedeemCode.code == code).with_for_update())
    if not row:
        raise HTTPException(404, "El código no es válido.")
    if not row.active:
        raise HTTPException(400, "Este código ya no está disponible.")
    if row.expires_at and row.expires_at <= now():
        raise HTTPException(400, "Este código venció.")
    if row.uses >= row.max_uses:
        raise HTTPException(400, "Este código ya alcanzó su límite de usos.")
    if db.scalar(select(Redemption.id).where(Redemption.code_id == row.id, Redemption.user_id == user.id)):
        raise HTTPException(400, "Ya canjeaste este código.")
    row.uses += 1
    db.add(Redemption(code_id=row.id, user_id=user.id))
    db.add(CreditEntry(user_id=user.id, delta=row.credits, reason="redeem", reference=f"redeem-{row.id}-{user.id}"))
    audit(db, user, "code_redeemed", str(row.id), credits=row.credits)
    db.flush()
    return {"added": row.credits, "balance": balance(db, user.id)}
