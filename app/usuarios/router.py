from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session
from app.db import database, SecuritySessionLocal
from app.models import LoginSession, User
from app.schemas import Login, Register, PasswordChange, SessionOut
from app.security import (COOKIE, DUMMY, audit, csrf, current_user, digest, hasher, ip_of,
                          login_session, new_session, password_ok, public_user, rate_limit)

router = APIRouter(prefix="/auth", tags=["usuarios"])


@router.get("/session", response_model=SessionOut)
def session(request: Request, response: Response, db: Session = Depends(database, scope="function")):
    from app.models import now
    token = request.cookies.get(COOKIE, "")
    s = db.get(LoginSession, digest(token)) if len(token) == 64 else None
    if not s or s.expires_at <= now():
        rate_limit("session", ip_of(request), 120, 60)
        if s:
            db.delete(s)
        s = new_session(db, response)
    user = db.get(User, s.user_id) if s.user_id else None
    return {"user": public_user(user) if user and user.active else None, "csrf": s.csrf}


@router.post("/login", response_model=SessionOut, dependencies=[Depends(csrf)])
def login(data: Login, request: Request, response: Response,
          previous: LoginSession = Depends(login_session), db: Session = Depends(database, scope="function")):
    identity = data.identity.strip().lower()
    rate_limit("login-ip", ip_of(request), 40, 900)
    rate_limit("login-account-ip", identity + ":" + ip_of(request), 10, 900)
    user = db.scalar(select(User).where(or_(User.username == identity, User.email == identity)).with_for_update())
    correct = password_ok(data.password, user.password_hash if user else DUMMY)
    if not user or not correct or not user.active:
        with SecuritySessionLocal.begin() as log:
            audit(log, None, "login_failed", digest(identity), ip_hash=digest(ip_of(request)))
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    db.delete(previous)
    s = new_session(db, response, user)
    audit(db, user, "login_success", str(user.id))
    return {"user": public_user(user), "csrf": s.csrf}


@router.post("/register", response_model=SessionOut, status_code=201, dependencies=[Depends(csrf)])
def register(data: Register, request: Request, response: Response,
             previous: LoginSession = Depends(login_session), db: Session = Depends(database, scope="function")):
    rate_limit("register", ip_of(request), 6, 3600)
    email = str(data.email).lower()
    if db.scalar(select(User.id).where(or_(User.username == data.username, User.email == email))):
        raise HTTPException(409, "No se puede registrar esa cuenta. Prueba iniciar sesión.")
    user = User(username=data.username, email=email, name=data.name, password_hash=hasher.hash(data.password))
    db.add(user)
    db.flush()
    db.delete(previous)
    s = new_session(db, response, user)
    audit(db, user, "register", str(user.id))
    return {"user": public_user(user), "csrf": s.csrf}


@router.post("/logout", dependencies=[Depends(csrf)])
def logout(response: Response, s: LoginSession = Depends(login_session), db: Session = Depends(database, scope="function")):
    db.delete(s)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.post("/password", dependencies=[Depends(csrf)])
def password(data: PasswordChange, response: Response, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rate_limit("password", str(user.id), 5, 900)
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not user.active:
        raise HTTPException(401, "Inicia sesión para continuar.")
    if not password_ok(data.current_password, user.password_hash):
        raise HTTPException(400, "La contraseña actual no es correcta.")
    user.password_hash = hasher.hash(data.new_password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    s = new_session(db, response, user)
    audit(db, user, "password_changed", str(user.id))
    return {"ok": True, "csrf": s.csrf}
