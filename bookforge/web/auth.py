"""Optional login for the MosiBooks web UI.

Enabled when MOSIBOOKS_PASSWORD is set (user: MOSIBOOKS_USER, default "admin").
With no password set the UI stays open, which is fine on 127.0.0.1 but not on a public host.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Body, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

COOKIE = "mosibooks_session"
MAX_AGE = 7 * 24 * 3600
PUBLIC = {"/login", "/api/login", "/api/auth/status"}
LOGIN_PAGE = Path(__file__).parent / "static" / "login.html"


def user() -> str:
    return os.environ.get("MOSIBOOKS_USER", "admin")


def enabled() -> bool:
    return bool(os.environ.get("MOSIBOOKS_PASSWORD"))


def _secret() -> bytes:
    return (os.environ.get("MOSIBOOKS_SECRET") or os.environ.get("MOSIBOOKS_PASSWORD", "")).encode()


def _sig(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    exp = str(int(time.time()) + MAX_AGE)
    return f"{exp}.{_sig(f'{user()}|{exp}')}"


def valid_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    return exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(sig, _sig(f"{user()}|{exp}"))


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def gate(request: Request, call_next):
        path = request.url.path
        if not enabled() or path in PUBLIC or valid_token(request.cookies.get(COOKIE)):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "not signed in"}, status_code=401)
        nxt = quote(path, safe="/") if path != "/" else ""
        return RedirectResponse("/login" + (f"?next={nxt}" if nxt else ""), status_code=302)

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(LOGIN_PAGE)

    @app.get("/api/auth/status")
    def status(request: Request):
        return {"enabled": enabled(), "signed_in": valid_token(request.cookies.get(COOKIE)), "user": user()}

    @app.post("/api/login")
    def login(request: Request, body: dict = Body(...)):
        ok = enabled() and _eq(str(body.get("username", "")), user()) \
            and _eq(str(body.get("password", "")), os.environ["MOSIBOOKS_PASSWORD"])
        if not ok:
            return JSONResponse({"detail": "Incorrect username or password"}, status_code=401)
        res = JSONResponse({"ok": True})
        res.set_cookie(COOKIE, make_token(), max_age=MAX_AGE, httponly=True, samesite="lax",
                       secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https")
        return res

    @app.post("/api/logout")
    def logout():
        res = JSONResponse({"ok": True})
        res.delete_cookie(COOKIE)
        return res
