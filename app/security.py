import hashlib
import hmac
import secrets
import time
from datetime import timedelta
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from cryptography.fernet import Fernet
from app import redis_client
from app.config import settings
from app.db import database
from app.models import Audit, LoginSession, User, now

COOKIE = "musedouble_local_session"
hasher = PasswordHasher()
DUMMY = hasher.hash("timing-only-invalid-account")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def encrypt(value: str) -> str:
    return Fernet(settings().encryption_key.get_secret_value().encode()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return Fernet(settings().encryption_key.get_secret_value().encode()).decrypt(value.encode()).decode()


def password_ok(raw: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, raw)
    except (VerificationError, InvalidHashError, ValueError):
        return False


# Sliding window in one atomic script: expire old events, check, then record.
# Rejected attempts are not recorded, so a blocked client cannot extend its own block.
_WINDOW_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, tonumber(ARGV[1]) - tonumber(ARGV[2]))
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return {0, oldest[2]}
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('PEXPIRE', KEYS[1], ARGV[2])
return {1, '0'}
"""
_window = None


def rate_limit(scope: str, key: str, limit: int, seconds: int):
    """Sliding window stored in Redis. Redis errors surface as 503 (see app/main.py)."""
    global _window
    hashed = digest(scope + ":" + key)
    now_ms = int(time.time() * 1000)
    if _window is None:
        _window = redis_client.client().register_script(_WINDOW_SCRIPT)
    allowed, oldest = _window(keys=[redis_client.key("rl:" + hashed)],
                              args=[now_ms, seconds * 1000, limit, secrets.token_hex(12)])
    if not int(allowed):
        retry = max(1, -(-(int(float(oldest)) + seconds * 1000 - now_ms) // 1000))
        raise HTTPException(429, "Demasiados intentos. Vuelve a intentarlo más tarde.", headers={"Retry-After": str(retry)})


def ip_of(request: Request) -> str:
    # Forwarded headers are not trusted; the local proxy connects through loopback.
    return request.client.host if request.client else "unknown"


def login_session(request: Request, db: Session = Depends(database, scope="function")) -> LoginSession:
    token = request.cookies.get(COOKIE, "")
    session = db.get(LoginSession, digest(token)) if len(token) == 64 else None
    if session is None or session.expires_at <= now():
        raise HTTPException(401, "Inicia sesión para continuar.")
    return session


def current_user(session: LoginSession = Depends(login_session), db: Session = Depends(database, scope="function")) -> User:
    user = db.get(User, session.user_id) if session.user_id else None
    if user is None or not user.active:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Se requiere una cuenta de administrador.")
    return user


def csrf(request: Request, session: LoginSession = Depends(login_session)):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in {settings().web_origin, settings().api_origin}:
        raise HTTPException(403, "Origen no permitido.")
    if not hmac.compare_digest(session.csrf, request.headers.get("x-csrf-token", "")):
        raise HTTPException(419, "La sesión del formulario ha caducado. Recarga la página.")


def new_session(db: Session, response: Response, user: User | None = None) -> LoginSession:
    token = secrets.token_hex(32)
    session = LoginSession(token_hash=digest(token), user_id=user.id if user else None,
                           csrf=secrets.token_hex(32), expires_at=now() + timedelta(hours=settings().session_hours))
    db.add(session)
    response.set_cookie(COOKIE, token, httponly=True, secure=settings().cookie_secure,
                        samesite="lax", max_age=settings().session_hours * 3600, path="/")
    return session


def audit(db: Session, actor: User | None, action: str, target: str = "", **details):
    db.add(Audit(actor_id=actor.id if actor else None, action=action, target=target, details=details))


def public_user(user: User):
    return {"id": str(user.id), "username": user.username, "email": user.email,
            "name": user.name, "role": user.role, "active": user.active, "can_generate": user.can_generate}
