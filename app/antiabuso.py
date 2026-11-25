import hashlib
import hmac
import ipaddress
import secrets
import smtplib
import time
from email.message import EmailMessage
import httpx
from fastapi import HTTPException, Request
from app import redis_client
from app.config import settings

TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
PWNED_URL = "https://api.pwnedpasswords.com/range/"
FORM_MAX_AGE = 2 * 3600
FAIL_WINDOW = 900
CAPTCHA_AFTER_FAILS = 3


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if settings().trusted_proxy:
        try:
            if ipaddress.ip_address(peer).is_loopback:
                forwarded = request.headers.get("x-real-ip", "").strip()
                if forwarded:
                    return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer


def _sign(value: str) -> str:
    return hmac.new(settings().signing_key.get_secret_value().encode(), ("form:" + value).encode(), hashlib.sha256).hexdigest()


def form_token() -> str:
    stamp = str(int(time.time()))
    return stamp + "." + _sign(stamp)


def check_form(token: str):
    stamp, _, signature = token.partition(".")
    if not stamp.isdigit() or not hmac.compare_digest(signature, _sign(stamp)):
        raise HTTPException(400, "No se pudo completar el registro. Recarga la página e inténtalo de nuevo.")
    age = time.time() - int(stamp)
    if age < settings().form_min_seconds or age > FORM_MAX_AGE:
        raise HTTPException(400, "No se pudo completar el registro. Recarga la página e inténtalo de nuevo.")


POW_TTL = 300
POW_MAX_EXTRA_BITS = 3


def turnstile_enabled() -> bool:
    return bool(settings().turnstile_secret.get_secret_value())


def captcha_enabled() -> bool:
    return turnstile_enabled() or settings().pow_enabled


def _pow_sign(body: str) -> str:
    return hmac.new(settings().signing_key.get_secret_value().encode(), ("pow:" + body).encode(), hashlib.sha256).hexdigest()


def new_challenge(ip: str) -> dict:
    extra = min(POW_MAX_EXTRA_BITS, failures("pow-issued", ip) // 5)
    add_failure("pow-issued", ip)
    bits = settings().pow_bits + extra
    body = f"{secrets.token_hex(12)}.{int(time.time()) + POW_TTL}.{bits}"
    return {"challenge": body + "." + _pow_sign(body), "bits": bits}


def _leading_zero_bits(data: bytes) -> int:
    count = 0
    for byte in data:
        if byte == 0:
            count += 8
            continue
        return count + (8 - byte.bit_length())
    return count


def check_pow(token: str):
    invalid = HTTPException(403, "No se pudo validar la verificación. Inténtalo de nuevo.")
    challenge, _, nonce = token.partition("|")
    parts = challenge.split(".")
    if len(parts) != 4 or not nonce or len(nonce) > 40 or not nonce.isalnum() or not all(p.isalnum() for p in parts):
        raise invalid
    salt, expires, bits, signature = parts
    if not hmac.compare_digest(signature, _pow_sign(".".join(parts[:3]))):
        raise invalid
    if not expires.isdigit() or not bits.isdigit() or int(expires) < time.time() or int(bits) < settings().pow_bits:
        raise invalid
    if _leading_zero_bits(hashlib.sha256((challenge + ":" + nonce).encode()).digest()) < int(bits):
        raise invalid
    if not redis_client.client().set(redis_client.key("pow:" + salt), "1", nx=True, ex=POW_TTL + 30):
        raise invalid


def verify_captcha(token: str, ip: str):
    if not captcha_enabled():
        return
    if not token or len(token) > 2048:
        raise HTTPException(403, "Completa la verificación para continuar.")
    if not turnstile_enabled():
        check_pow(token)
        return
    try:
        r = httpx.post(TURNSTILE_URL, data={"secret": settings().turnstile_secret.get_secret_value(), "response": token, "remoteip": ip}, timeout=6)
        ok = r.status_code == 200 and r.json().get("success") is True
    except (httpx.HTTPError, ValueError):
        ok = False
    if not ok:
        raise HTTPException(403, "No se pudo validar la verificación. Inténtalo de nuevo.")


def pwned_count(password: str) -> int:
    if not settings().pwned_check:
        return 0
    digest = hashlib.sha1(password.encode()).hexdigest().upper()
    try:
        r = httpx.get(PWNED_URL + digest[:5], headers={"Add-Padding": "true"}, timeout=4)
        if r.status_code != 200:
            return 0
        for line in r.text.splitlines():
            suffix, _, count = line.partition(":")
            if suffix == digest[5:]:
                return int(count)
    except (httpx.HTTPError, ValueError):
        return 0
    return 0


def reject_pwned(password: str):
    if pwned_count(password) > 0:
        raise HTTPException(400, "Esa contraseña aparece en filtraciones conocidas. Elige otra.")


def failures(scope: str, key: str) -> int:
    value = redis_client.client().get(redis_client.key("fail:" + scope + ":" + hashlib.sha256(key.encode()).hexdigest()))
    return int(value or 0)


def add_failure(scope: str, key: str):
    name = redis_client.key("fail:" + scope + ":" + hashlib.sha256(key.encode()).hexdigest())
    pipe = redis_client.client().pipeline()
    pipe.incr(name)
    pipe.expire(name, FAIL_WINDOW)
    pipe.execute()


def clear_failures(scope: str, key: str):
    redis_client.client().delete(redis_client.key("fail:" + scope + ":" + hashlib.sha256(key.encode()).hexdigest()))


def mail_enabled() -> bool:
    return bool(settings().smtp_host and settings().mail_from)


def send_mail(to: str, subject: str, body: str):
    if not mail_enabled():
        return
    s = settings()
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = s.mail_from, to, subject
    message.set_content(body)
    try:
        smtp = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=15) if s.smtp_port == 465 else smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15)
        with smtp:
            if s.smtp_port != 465:
                smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password.get_secret_value())
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return
