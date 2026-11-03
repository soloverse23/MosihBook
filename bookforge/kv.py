"""A tiny key-value store for accounts and per-user settings.

Upstash Redis (REST) when its env vars are set - Vercel's Upstash integration sets KV_REST_API_URL /
KV_REST_API_TOKEN, a direct Upstash database UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN - so the
data survives restarts and Vercel cold starts. Otherwise a JSON file next to the studio settings.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request
from pathlib import Path

_lock = threading.Lock()


def _upstash() -> tuple[str, str] | None:
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return (url.rstrip("/"), token) if url and token else None


def persistent() -> bool:
    """True when data survives restarts (Upstash, or a local disk outside Vercel)."""
    from . import settings
    return bool(_upstash()) or not settings.ON_VERCEL


def _cmd(*args: str):
    url, token = _upstash()
    req = urllib.request.Request(url, json.dumps(list(args)).encode(),
                                 {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(f"Upstash: {out['error']}")
    return out.get("result")


def _file() -> Path:
    from . import settings
    return settings.PATH.parent / "kv.json"


def _read() -> dict:
    f = _file()
    return json.loads(f.read_text()) if f.exists() else {}


def get(key: str):
    if _upstash():
        v = _cmd("GET", key)
        return json.loads(v) if v is not None else None
    with _lock:
        return _read().get(key)


def set(key: str, value, only_if_new: bool = False) -> bool:
    """Store a JSON value. `only_if_new`: do nothing (return False) when the key exists."""
    if _upstash():
        args = ["SET", key, json.dumps(value)] + (["NX"] if only_if_new else [])
        return _cmd(*args) is not None
    with _lock:
        data = _read()
        if only_if_new and key in data:
            return False
        data[key] = value
        f = _file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))
        f.chmod(0o600)
        return True


def delete(key: str) -> None:
    if _upstash():
        _cmd("DEL", key)
        return
    with _lock:
        data = _read()
        if data.pop(key, None) is not None:
            _file().write_text(json.dumps(data))
