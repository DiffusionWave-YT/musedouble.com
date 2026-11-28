import secrets
import time
from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session
from app import antiabuso
from app.config import settings
from app.db import database, SecuritySessionLocal
from app.models import EmailToken, LoginSession, User, now
from app.schemas import Forgot, Login, Register, PasswordChange, Reset, SessionOut, TokenInput
from app.security import (COOKIE, DUMMY, audit, csrf, current_user, digest, hasher, ip_of,
                          login_session, new_session, password_ok, public_user, rate_limit)

router = APIRouter(prefix="/auth", tags=["usuarios"])
CAPTCHA_NEEDED = "Completa la verificación para continuar."


def issue_token(db: Session, user: User, purpose: str, minutes: int) -> str:
    db.execute(delete(EmailToken).where(or_(EmailToken.expires_at <= now(), (EmailToken.user_id == user.id) & (EmailToken.purpose == purpose))))
    raw = secrets.token_urlsafe(32)
    db.add(EmailToken(token_hash=digest(raw), user_id=user.id, purpose=purpose, expires_at=now() + timedelta(minutes=minutes)))
    return raw


def send_verification(user: User, raw: str):
    antiabuso.send_mail(user.email, "Confirma tu correo en MuseDouble",
                        "Para confirmar tu correo abre este enlace (vale 24 horas):\n\n" + settings().web_origin + "/verify-email?token=" + raw + "\n\nSi no creaste la cuenta, ignora este mensaje.")


def send_reset(user: User, raw: str):
    antiabuso.send_mail(user.email, "Restablece tu contraseña de MuseDouble",
                        "Para elegir una contraseña nueva abre este enlace (vale 30 minutos):\n\n" + settings().web_origin + "/reset-password?token=" + raw + "\n\nSi no lo pediste, ignora este mensaje.")


@router.get("/config")
def config(request: Request):
    rate_limit("auth-config", ip_of(request), 60, 60)
    return {"captcha": settings().turnstile_site_key if antiabuso.turnstile_enabled() else None,
            "pow": settings().pow_enabled and not antiabuso.turnstile_enabled(),
            "form": antiabuso.form_token(), "mail": antiabuso.mail_enabled()}


@router.get("/challenge")
def challenge(request: Request):
    ip = ip_of(request)
    rate_limit("challenge", ip, 30, 60)
    return antiabuso.new_challenge(ip)


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
    ip = ip_of(request)
    rate_limit("login-ip", ip, 40, 900)
    rate_limit("login-account-ip", identity + ":" + ip, 10, 900)
    streak = max(antiabuso.failures("login-ip", ip), antiabuso.failures("login-identity", identity))
    if streak >= antiabuso.CAPTCHA_AFTER_FAILS:
        if antiabuso.captcha_enabled():
            antiabuso.verify_captcha(data.captcha, ip)
        else:
            time.sleep(min(streak - antiabuso.CAPTCHA_AFTER_FAILS + 1, 4))
    user = db.scalar(select(User).where(or_(User.username == identity, User.email == identity)).with_for_update())
    correct = password_ok(data.password, user.password_hash if user else DUMMY)
    if not user or not correct or not user.active:
        antiabuso.add_failure("login-ip", ip)
        antiabuso.add_failure("login-identity", identity)
        with SecuritySessionLocal.begin() as log:
            audit(log, None, "login_failed", digest(identity), ip_hash=digest(ip))
        if antiabuso.captcha_enabled() and max(antiabuso.failures("login-ip", ip), antiabuso.failures("login-identity", identity)) >= antiabuso.CAPTCHA_AFTER_FAILS:
            raise HTTPException(403, CAPTCHA_NEEDED)
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    antiabuso.clear_failures("login-identity", identity)
    db.delete(previous)
    s = new_session(db, response, user)
    audit(db, user, "login_success", str(user.id))
    return {"user": public_user(user), "csrf": s.csrf}


@router.post("/register", response_model=SessionOut, status_code=201, dependencies=[Depends(csrf)])
def register(data: Register, request: Request, response: Response, tasks: BackgroundTasks,
             previous: LoginSession = Depends(login_session), db: Session = Depends(database, scope="function")):
    ip = ip_of(request)
    rate_limit("register", ip, settings().register_per_ip_hour, 3600)
    rate_limit("register-day", ip, settings().register_per_ip_day, 86400)
    if data.website:
        with SecuritySessionLocal.begin() as log:
            audit(log, None, "register_honeypot", digest(ip))
        raise HTTPException(400, "No se pudo completar el registro. Recarga la página e inténtalo de nuevo.")
    antiabuso.check_form(data.form)
    antiabuso.verify_captcha(data.captcha, ip)
    antiabuso.reject_pwned(data.password)
    email = str(data.email).lower()
    if db.scalar(select(User.id).where(or_(User.username.in_([data.username, email]), User.email.in_([email, data.username])))):
        raise HTTPException(409, "No se puede registrar esa cuenta. Prueba iniciar sesión.")
    user = User(username=data.username, email=email, name=data.name, password_hash=hasher.hash(data.password), can_generate=True, email_verified=not antiabuso.mail_enabled())
    db.add(user)
    db.flush()
    db.delete(previous)
    s = new_session(db, response, user)
    audit(db, user, "register", str(user.id))
    if not user.email_verified:
        tasks.add_task(send_verification, user, issue_token(db, user, "verify", 1440))
    return {"user": public_user(user), "csrf": s.csrf}


@router.post("/verify-email", dependencies=[Depends(csrf)])
def verify_email(data: TokenInput, request: Request, db: Session = Depends(database, scope="function")):
    rate_limit("verify-email", ip_of(request), 20, 900)
    row = db.scalar(select(EmailToken).where(EmailToken.token_hash == digest(data.token), EmailToken.purpose == "verify").with_for_update())
    if not row or row.expires_at <= now():
        raise HTTPException(400, "El enlace no es válido o ya venció.")
    user = db.get(User, row.user_id)
    user.email_verified = True
    db.delete(row)
    audit(db, user, "email_verified", str(user.id))
    return {"ok": True}


@router.post("/resend-verification", dependencies=[Depends(csrf)])
def resend_verification(tasks: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rate_limit("resend-verification", str(user.id), 3, 3600)
    if not user.email_verified and user.email and antiabuso.mail_enabled():
        tasks.add_task(send_verification, user, issue_token(db, user, "verify", 1440))
    return {"ok": True}


@router.post("/forgot", dependencies=[Depends(csrf)])
def forgot(data: Forgot, request: Request, tasks: BackgroundTasks, db: Session = Depends(database, scope="function")):
    ip = ip_of(request)
    identity = data.identity.strip().lower()
    rate_limit("forgot-ip", ip, 8, 3600)
    rate_limit("forgot-identity", identity, 3, 3600)
    antiabuso.verify_captcha(data.captcha, ip)
    user = db.scalar(select(User).where(or_(User.username == identity, User.email == identity)))
    if user and user.active and user.email and user.role != "admin" and antiabuso.mail_enabled():
        tasks.add_task(send_reset, user, issue_token(db, user, "reset", 30))
        audit(db, user, "password_reset_requested", str(user.id))
    return {"ok": True}


@router.post("/reset", dependencies=[Depends(csrf)])
def reset(data: Reset, request: Request, db: Session = Depends(database, scope="function")):
    rate_limit("reset-ip", ip_of(request), 10, 900)
    antiabuso.reject_pwned(data.password)
    row = db.scalar(select(EmailToken).where(EmailToken.token_hash == digest(data.token), EmailToken.purpose == "reset").with_for_update())
    if not row or row.expires_at <= now():
        raise HTTPException(400, "El enlace no es válido o ya venció.")
    user = db.scalar(select(User).where(User.id == row.user_id).with_for_update())
    user.password_hash = hasher.hash(data.password)
    user.email_verified = True
    db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    audit(db, user, "password_reset", str(user.id))
    return {"ok": True}


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
    antiabuso.reject_pwned(data.new_password)
    user.password_hash = hasher.hash(data.new_password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    s = new_session(db, response, user)
    audit(db, user, "password_changed", str(user.id))
    return {"ok": True, "csrf": s.csrf}
