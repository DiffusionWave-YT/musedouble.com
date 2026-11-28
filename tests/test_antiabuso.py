import hashlib
import re
import httpx
import pytest
from app import antiabuso
from app.config import settings
from app.main import application
from fastapi.testclient import TestClient

GOOD = "test-only-long-password"


def person(name="ana", **extra):
    return {"username": name, "name": name.title(), "email": name + "@example.com", "password": GOOD, **extra}


def test_honeypot_and_form_token(environment):
    env = environment
    c = env["Client"]()
    assert c.signup(person("bot"), website="http://spam.example").status_code == 400
    assert c.call("/auth/register", "POST", {**person("nofrm"), "form": ""}).status_code == 400
    assert c.call("/auth/register", "POST", {**person("forged"), "form": "1.deadbeef"}).status_code == 400
    assert c.signup(person("human")).status_code == 201


def test_form_too_fast_is_rejected(environment, monkeypatch):
    c = environment["Client"]()
    monkeypatch.setattr(settings(), "form_min_seconds", 60)
    assert c.signup(person("quick")).status_code == 400


def test_registration_caps_per_ip_day(environment, monkeypatch):
    env = environment
    monkeypatch.setattr(settings(), "register_per_ip_hour", 100)
    monkeypatch.setattr(settings(), "register_per_ip_day", 3)
    for i in range(3):
        assert env["Client"]().signup(person("day%d" % i)).status_code == 201
    r = env["Client"]().signup(person("day3"))
    assert r.status_code == 429 and r.headers.get("Retry-After")


class Verdict:
    def __init__(self, ok):
        self.ok = ok
        self.status_code = 200

    def json(self):
        return {"success": self.ok}


def test_captcha_enforced_on_register_login_and_forgot(environment, monkeypatch):
    env = environment
    monkeypatch.setattr(settings(), "turnstile_secret", type(settings().turnstile_secret)("secret"))
    monkeypatch.setattr(settings(), "turnstile_site_key", "site")
    monkeypatch.setattr(antiabuso.httpx, "post", lambda url, data, timeout: Verdict(data["response"] == "good"))
    c = env["Client"]()
    assert c.call("/auth/config").json()["captcha"] == "site"
    assert c.signup(person("cap1")).status_code == 403
    assert c.signup(person("cap1"), captcha="bad").status_code == 403
    assert c.signup(person("cap1"), captcha="good").status_code == 201
    other = env["Client"]()
    assert other.call("/auth/forgot", "POST", {"identity": "cap1"}).status_code == 403
    assert other.call("/auth/forgot", "POST", {"identity": "cap1", "captcha": "good"}).status_code == 200
    for _ in range(3):
        last = other.call("/auth/login", "POST", {"identity": "cap1", "password": "wrong-password-x"})
    assert last.status_code == 403
    assert other.call("/auth/login", "POST", {"identity": "cap1", "password": GOOD}).status_code == 403
    assert other.call("/auth/login", "POST", {"identity": "cap1", "password": GOOD, "captcha": "good"}).status_code == 200


def test_login_without_any_captcha_adds_delay(environment, monkeypatch):
    env = environment
    monkeypatch.setattr(settings(), "pow_enabled", False)
    pauses = []
    monkeypatch.setattr("app.usuarios.router.time.sleep", lambda s: pauses.append(s))
    c = env["Client"]()
    for _ in range(5):
        assert c.call("/auth/login", "POST", {"identity": "nobody", "password": "wrong-password-x"}).status_code == 401
    assert pauses and pauses == sorted(pauses) and max(pauses) <= 4


def test_pwned_passwords_rejected(environment, monkeypatch):
    env = environment
    monkeypatch.setattr(settings(), "pwned_check", True)
    sha = hashlib.sha1(GOOD.encode()).hexdigest().upper()
    seen = []

    def fake(url, headers, timeout):
        seen.append(url)
        body = sha[5:] + ":42\r\n" + "0" * 35 + ":1\r\n"
        return type("R", (), {"status_code": 200, "text": body})()

    monkeypatch.setattr(antiabuso.httpx, "get", fake)
    r = env["Client"]().signup(person("leaked"))
    assert r.status_code == 400 and "filtraciones" in r.json()["detail"]
    assert seen == [antiabuso.PWNED_URL + sha[:5]] and sha[5:] not in seen[0]
    monkeypatch.setattr(antiabuso.httpx, "get", lambda url, headers, timeout: (_ for _ in ()).throw(httpx.ConnectError("down")))
    assert env["Client"]().signup(person("offline")).status_code == 201


def test_real_ip_only_from_trusted_proxy(environment, monkeypatch):
    class Req:
        def __init__(self, host, headers):
            self.client = type("C", (), {"host": host})()
            self.headers = headers

    assert antiabuso.client_ip(Req("127.0.0.1", {"x-real-ip": "203.0.113.9"})) == "127.0.0.1"
    monkeypatch.setattr(settings(), "trusted_proxy", True)
    assert antiabuso.client_ip(Req("127.0.0.1", {"x-real-ip": "203.0.113.9"})) == "203.0.113.9"
    assert antiabuso.client_ip(Req("198.51.100.4", {"x-real-ip": "203.0.113.9"})) == "198.51.100.4"
    assert antiabuso.client_ip(Req("127.0.0.1", {"x-real-ip": "not-an-ip"})) == "127.0.0.1"


def mailbox(monkeypatch):
    sent = []
    monkeypatch.setattr(settings(), "smtp_host", "smtp.test")
    monkeypatch.setattr(settings(), "mail_from", "no-reply@example.com")
    monkeypatch.setattr(antiabuso, "send_mail", lambda to, subject, body: sent.append((to, body)))
    return sent


def link_token(body):
    return re.search(r"token=([\w-]+)", body).group(1)


def test_email_verification_gates_and_confirms(environment, monkeypatch):
    env = environment
    sent = mailbox(monkeypatch)
    c = env["Client"]()
    r = c.signup(person("newbie"))
    assert r.status_code == 201 and r.json()["user"]["email_verified"] is False
    assert len(sent) == 1 and sent[0][0] == "newbie@example.com"
    assert c.call("/credits/redeem", "POST", {"code": "ANYCODE"}).status_code == 403
    assert c.call("/auth/verify-email", "POST", {"token": "x" * 30}).status_code == 400
    token = link_token(sent[0][1])
    assert c.call("/auth/verify-email", "POST", {"token": token}).status_code == 200
    assert c.call("/auth/verify-email", "POST", {"token": token}).status_code == 400
    assert c.call("/auth/session").json()["user"]["email_verified"] is True
    assert c.call("/credits/redeem", "POST", {"code": "ANYCODE"}).status_code == 404


def test_resend_verification_is_limited(environment, monkeypatch):
    env = environment
    sent = mailbox(monkeypatch)
    c = env["Client"]()
    assert c.signup(person("again")).status_code == 201
    for _ in range(3):
        assert c.call("/auth/resend-verification", "POST").status_code == 200
    assert c.call("/auth/resend-verification", "POST").status_code == 429
    assert len(sent) == 4


def test_password_recovery_is_single_use_and_generic(environment, monkeypatch):
    env = environment
    sent = mailbox(monkeypatch)
    c = env["Client"]()
    assert c.signup(person("forgetful")).status_code == 201
    sent.clear()
    guest = env["Client"]()
    ghost = guest.call("/auth/forgot", "POST", {"identity": "nobody-here", "captcha": guest.pow()})
    real = guest.call("/auth/forgot", "POST", {"identity": "forgetful@example.com", "captcha": guest.pow()})
    assert ghost.status_code == real.status_code == 200 and ghost.json() == real.json()
    assert len(sent) == 1
    token = link_token(sent[0][1])
    assert guest.call("/auth/reset", "POST", {"token": token, "password": "short"}).status_code == 422
    assert guest.call("/auth/reset", "POST", {"token": token, "password": "brand-new-password-9"}).status_code == 200
    assert guest.call("/auth/reset", "POST", {"token": token, "password": "another-password-10"}).status_code == 400
    assert c.call("/auth/session").json()["user"] is None
    fresh = env["Client"]()
    assert fresh.call("/auth/login", "POST", {"identity": "forgetful", "password": GOOD}).status_code == 401
    assert fresh.call("/auth/login", "POST", {"identity": "forgetful", "password": "brand-new-password-9"}).status_code == 200


def test_recovery_never_applies_to_administrators(environment, monkeypatch):
    env = environment
    sent = mailbox(monkeypatch)
    with env["sessions"]() as db:
        from app.models import User
        from sqlalchemy import select
        admin = db.scalar(select(User).where(User.username == "admin_test"))
        admin.email = "admin@example.com"
        db.commit()
    guest = env["Client"]()
    assert guest.call("/auth/forgot", "POST", {"identity": "admin@example.com", "captcha": guest.pow()}).status_code == 200
    assert sent == []


def test_reset_with_expired_token_fails(environment, monkeypatch):
    env = environment
    sent = mailbox(monkeypatch)
    assert env["Client"]().signup(person("late")).status_code == 201
    sent.clear()
    guest = env["Client"]()
    guest.call("/auth/forgot", "POST", {"identity": "late", "captcha": guest.pow()})
    token = link_token(sent[0][1])
    with env["sessions"]() as db:
        from datetime import timedelta
        from sqlalchemy import update
        from app.models import EmailToken, now
        db.execute(update(EmailToken).values(expires_at=now() - timedelta(minutes=1)))
        db.commit()
    assert guest.call("/auth/reset", "POST", {"token": token, "password": "brand-new-password-9"}).status_code == 400


def test_pow_challenge_is_required_and_single_use(environment):
    env = environment
    c = env["Client"]()
    assert c.call("/auth/config").json()["pow"] is True
    missing = c.call("/auth/register", "POST", {**person("nopow"), "form": c.call("/auth/config").json()["form"]})
    assert missing.status_code == 403
    token = c.pow()
    form = c.call("/auth/config").json()["form"]
    assert c.call("/auth/register", "POST", {**person("powok"), "form": form, "captcha": token}).status_code == 201
    again = env["Client"]()
    replay = again.call("/auth/register", "POST", {**person("powtwo"), "form": again.call("/auth/config").json()["form"], "captcha": token})
    assert replay.status_code == 403


def test_pow_rejects_forged_expired_and_weak_solutions(environment, monkeypatch):
    import time
    env = environment
    c = env["Client"]()
    given = c.call("/auth/challenge").json()
    assert given["bits"] == 4 and given["challenge"].count(".") == 3
    forged = given["challenge"].rsplit(".", 1)[0] + "." + "0" * 64
    with pytest.raises(Exception) as bad:
        antiabuso.check_pow(forged + "|1")
    assert bad.value.status_code == 403
    old = c.pow()
    real = time.time
    monkeypatch.setattr(antiabuso.time, "time", lambda: real() + antiabuso.POW_TTL + 10)
    with pytest.raises(Exception) as late:
        antiabuso.check_pow(old)
    assert late.value.status_code == 403
    monkeypatch.setattr(antiabuso.time, "time", real)
    easy = c.pow()
    monkeypatch.setattr(settings(), "pow_bits", 12)
    with pytest.raises(Exception) as weak:
        antiabuso.check_pow(easy)
    assert weak.value.status_code == 403


def test_pow_difficulty_rises_under_pressure_and_is_rate_limited(environment):
    env = environment
    c = env["Client"]()
    bits = [c.call("/auth/challenge").json()["bits"] for _ in range(21)]
    assert bits[0] == 4 and bits[-1] == 4 + antiabuso.POW_MAX_EXTRA_BITS and bits == sorted(bits)
    for _ in range(9):
        c.call("/auth/challenge")
    assert c.call("/auth/challenge").status_code == 429


def test_login_asks_for_pow_after_repeated_failures(environment):
    env = environment
    c = env["Client"]()
    assert c.signup(person("pwuser")).status_code == 201
    other = env["Client"]()
    codes = [other.call("/auth/login", "POST", {"identity": "pwuser", "password": "wrong-password-x"}).status_code for _ in range(3)]
    assert codes == [401, 401, 403]
    assert other.call("/auth/login", "POST", {"identity": "pwuser", "password": GOOD}).status_code == 403
    assert other.call("/auth/login", "POST", {"identity": "pwuser", "password": GOOD, "captcha": other.pow()}).status_code == 200


def fake_socket(resolver):
    import socket
    from types import SimpleNamespace
    return SimpleNamespace(getaddrinfo=resolver, gaierror=socket.gaierror, SOCK_STREAM=socket.SOCK_STREAM)


def test_gpu_hosts_accept_public_names_and_block_internal_ones(environment, monkeypatch):
    import socket
    from fastapi import HTTPException
    from app import comfy
    monkeypatch.setattr(settings(), "allowed_gpu_hosts", "127.0.0.1,localhost")
    table = {"conector_1.example.ai": "93.184.216.34", "inside.example.ai": "10.0.0.7", "mixed.example.ai": "93.184.216.34,192.168.1.5"}

    def fake(host, port, type=0):
        if host not in table:
            raise socket.gaierror("no such host")
        return [(2, 1, 6, "", (ip, port)) for ip in table[host].split(",")]

    monkeypatch.setattr(comfy, "socket", fake_socket(fake))
    assert comfy.validate_url("https://conector_1.example.ai/", resolve=True) == "https://conector_1.example.ai"
    assert comfy.validate_url("http://8.8.8.8:8188") == "http://8.8.8.8:8188"
    for bad in ("https://inside.example.ai", "https://mixed.example.ai", "http://10.1.2.3:8188", "http://169.254.169.254/x",
                "http://[::1]:8188", "http://192.168.0.5", "ftp://conector_1.example.ai", "https://user:pw@conector_1.example.ai"):
        with pytest.raises(HTTPException):
            comfy.validate_url(bad, resolve=True)
    with pytest.raises(HTTPException):
        comfy.validate_url("https://unknown.example.ai", resolve=True)
    assert comfy.validate_url("http://127.0.0.1:8188", resolve=True) == "http://127.0.0.1:8188"


def test_gpu_requests_refuse_hosts_that_turn_private_later(environment, monkeypatch):
    import socket
    from types import SimpleNamespace
    from app import comfy
    from app.security import encrypt
    monkeypatch.setattr(settings(), "allowed_gpu_hosts", "localhost")
    ips = {"value": "93.184.216.34"}
    monkeypatch.setattr(comfy, "socket", fake_socket(lambda host, port, type=0: [(2, 1, 6, "", (ips["value"], port))]))
    client = comfy.ComfyClient(SimpleNamespace(url_enc=encrypt("https://rebind.example.ai"), token_enc=None))
    ips["value"] = "127.0.0.1"
    with pytest.raises(comfy.ComfyError) as blocked:
        client.json("/system_stats")
    assert blocked.value.code == "private_network" and blocked.value.retryable is False
