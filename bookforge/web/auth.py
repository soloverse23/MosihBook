"""Sign-in for the MosiBooks web UI. Three modes:

- accounts: each person creates an account (email + password, with the invite code in
  MOSIBOOKS_INVITE_CODE) and gets their own settings, API keys and books. On whenever an invite code is
  set, and always on Vercel (with no code set there, sign-up is closed).
- password: one shared login, MOSIBOOKS_USER (default "admin") / MOSIBOOKS_PASSWORD.
- open: nothing set - fine on 127.0.0.1, not on a public host.

Accounts live in the key-value store (bookforge/kv.py: Upstash Redis on Vercel). Passwords are stored
as salted PBKDF2-SHA256 hashes. Sessions are signed cookies (MOSIBOOKS_SECRET, or a random secret kept
in the store).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Body, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from .. import kv, settings

COOKIE = "mosibooks_session"
MAX_AGE = 14 * 24 * 3600
PUBLIC = {"/login", "/api/login", "/api/signup", "/api/auth/status"}
LOGIN_PAGE = Path(__file__).parent / "static" / "login.html"
ITERATIONS = 240_000
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def invite_code() -> str:
    return os.environ.get("MOSIBOOKS_INVITE_CODE", "").strip()


def mode() -> str:
    if invite_code() or settings.ON_VERCEL:
        return "accounts"
    return "password" if os.environ.get("MOSIBOOKS_PASSWORD") else "open"


def enabled() -> bool:
    return mode() != "open"


def user() -> str:
    return os.environ.get("MOSIBOOKS_USER", "admin")


_secret_cache: bytes | None = None


def _secret() -> bytes:
    global _secret_cache
    if env := os.environ.get("MOSIBOOKS_SECRET"):
        return env.encode()
    if mode() == "password":
        return os.environ.get("MOSIBOOKS_PASSWORD", "").encode()
    if _secret_cache is None:  # one random secret per server, kept in the store so sessions survive restarts
        kv.set("server:session_secret", secrets.token_hex(32), only_if_new=True)
        _secret_cache = kv.get("server:session_secret").encode()
    return _secret_cache


def _sig(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(who: str | None = None) -> str:
    who = who or user()
    exp = str(int(time.time()) + MAX_AGE)
    name = base64.urlsafe_b64encode(who.encode()).decode().rstrip("=")
    return f"{name}.{exp}.{_sig(f'{who}|{exp}')}"


def token_user(token: str | None) -> str | None:
    """The account (or shared user) a session cookie belongs to, if it is valid and not expired."""
    try:
        name, exp, sig = (token or "").split(".")
        who = base64.urlsafe_b64decode(name + "=" * (-len(name) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    if not (exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(sig, _sig(f"{who}|{exp}"))):
        return None
    if mode() == "accounts":
        return who if kv.get(f"user:{who}") else None
    return who if who == user() else None


def valid_token(token: str | None) -> bool:
    return token_user(token) is not None


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()


def create_account(email: str, password: str, invite: str) -> str:
    """Returns the normalized email; raises ValueError with a message for the person signing up."""
    email = email.strip().lower()
    if not invite_code():
        raise PermissionError("Sign-up is closed on this server (no invite code is set).")
    if not _eq(invite.strip(), invite_code()):
        raise PermissionError("That invite code isn't right.")
    if not EMAIL.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Use a password of at least 8 characters.")
    salt = secrets.token_hex(16)
    record = {"email": email, "salt": salt, "hash": _hash(password, salt), "created": time.time()}
    if not kv.set(f"user:{email}", record, only_if_new=True):
        raise FileExistsError("An account with this email already exists. Sign in instead.")
    return email


def check_login(username: str, password: str) -> str | None:
    if mode() == "accounts":
        email = username.strip().lower()
        rec = kv.get(f"user:{email}") if email else None
        if rec and _eq(_hash(password, rec["salt"]), rec["hash"]):
            return email
        return None
    if mode() == "password" and _eq(username, user()) and _eq(password, os.environ["MOSIBOOKS_PASSWORD"]):
        return user()
    return None


def _session(request: Request, who: str) -> JSONResponse:
    res = JSONResponse({"ok": True, "user": who})
    res.set_cookie(COOKIE, make_token(who), max_age=MAX_AGE, httponly=True, samesite="lax",
                   secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https")
    return res


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def gate(request: Request, call_next):
        path = request.url.path
        if not enabled() or path in PUBLIC:
            return await call_next(request)
        who = token_user(request.cookies.get(COOKIE))
        if who:
            # each account sees only its own settings, keys and books for this request
            ctx = settings.current_user.set(who if mode() == "accounts" else None)
            try:
                return await call_next(request)
            finally:
                settings.current_user.reset(ctx)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "not signed in"}, status_code=401)
        nxt = quote(path, safe="/") if path != "/" else ""
        return RedirectResponse("/login" + (f"?next={nxt}" if nxt else ""), status_code=302)

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(LOGIN_PAGE)

    @app.get("/api/auth/status")
    def status(request: Request):
        who = token_user(request.cookies.get(COOKIE)) if enabled() else None
        return {"enabled": enabled(), "mode": mode(), "signed_in": bool(who), "user": who or user(),
                "signup_open": mode() == "accounts" and bool(invite_code()),
                "persistent": kv.persistent(),
                # troubleshooting: what this deploy can see (names only, never values)
                "invite_code_set": bool(invite_code()), "database": kv.backend(),
                "database_env": kv.seen_env() if mode() == "accounts" else []}

    @app.post("/api/signup")
    def signup(request: Request, body: dict = Body(...)):
        if mode() != "accounts":
            return JSONResponse({"detail": "This server has no accounts"}, status_code=404)
        try:
            email = create_account(str(body.get("email", "")), str(body.get("password", "")),
                                   str(body.get("invite", "")))
        except PermissionError as e:
            return JSONResponse({"detail": str(e)}, status_code=403)
        except FileExistsError as e:
            return JSONResponse({"detail": str(e)}, status_code=409)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=422)
        return _session(request, email)

    @app.post("/api/login")
    def login(request: Request, body: dict = Body(...)):
        who = check_login(str(body.get("username") or body.get("email") or ""), str(body.get("password", "")))
        if not who:
            time.sleep(0.6)  # slow down password guessing
            return JSONResponse({"detail": "Incorrect email or password" if mode() == "accounts"
                                 else "Incorrect username or password"}, status_code=401)
        return _session(request, who)

    @app.post("/api/logout")
    def logout():
        res = JSONResponse({"ok": True})
        res.delete_cookie(COOKIE)
        return res
