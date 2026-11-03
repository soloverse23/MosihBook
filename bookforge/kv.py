"""A tiny key-value store for accounts and per-user settings.

Survives restarts and Vercel cold starts when a Redis database is connected:
- Upstash over REST: KV_REST_API_URL / KV_REST_API_TOKEN (Vercel's Upstash integration, also with a custom
  prefix such as STORAGE_KV_REST_API_URL) or UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN;
- any Redis by URL: REDIS_URL or KV_URL (Vercel's Redis Cloud integration, or Upstash's redis:// URL).
Otherwise a JSON file next to the studio settings.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request
from pathlib import Path

_lock = threading.Lock()


def _upstash() -> tuple[str, str] | None:
    env = os.environ
    for url_key in sorted(k for k in env if k.endswith("REST_API_URL") or k.endswith("REDIS_REST_URL")):
        token_key = url_key[: -len("URL")] + "TOKEN"
        if env.get(url_key) and env.get(token_key) and "READ_ONLY" not in token_key:
            return env[url_key].rstrip("/"), env[token_key]
    return None


def _redis_url() -> str | None:
    env = os.environ
    for k in ["REDIS_URL", "KV_URL"] + sorted(k for k in env if k.endswith("_REDIS_URL") or k.endswith("_KV_URL")):
        if env.get(k, "").startswith(("redis://", "rediss://")):
            return env[k]
    return None


_client = None


def _redis():
    global _client
    if _client is None:
        import redis
        _client = redis.Redis.from_url(_redis_url(), decode_responses=True, socket_timeout=10)
    return _client


def backend() -> str:
    return "upstash" if _upstash() else "redis" if _redis_url() else "file"


def persistent() -> bool:
    """True when data survives restarts (a Redis database, or a local disk outside Vercel)."""
    from . import settings
    return backend() != "file" or not settings.ON_VERCEL


def seen_env() -> list[str]:
    """Names (never values) of the database variables this server can see, for troubleshooting."""
    return sorted(k for k in os.environ if any(w in k for w in ("KV_", "REDIS", "UPSTASH")))


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
    if _upstash() or _redis_url():
        v = _cmd("GET", key) if _upstash() else _redis().get(key)
        return json.loads(v) if v is not None else None
    with _lock:
        return _read().get(key)


def set(key: str, value, only_if_new: bool = False) -> bool:
    """Store a JSON value. `only_if_new`: do nothing (return False) when the key exists."""
    if _upstash():
        args = ["SET", key, json.dumps(value)] + (["NX"] if only_if_new else [])
        return _cmd(*args) is not None
    if _redis_url():
        return bool(_redis().set(key, json.dumps(value), nx=only_if_new))
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
    if _redis_url():
        _redis().delete(key)
        return
    with _lock:
        data = _read()
        if data.pop(key, None) is not None:
            _file().write_text(json.dumps(data))
