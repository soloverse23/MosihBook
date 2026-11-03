"""Studio settings: API keys and defaults, stored in ~/.bookforge/settings.json (owner-only).

With accounts (see web/auth.py) every signed-in person has their own settings, keys and books: the
request's account is held in `current_user`, settings live in the key-value store (bookforge/kv.py) and
files under BASE/users/<id>/.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from pydantic import BaseModel

from . import kdp

# on Vercel only /tmp is writable (and it is wiped between cold starts)
ON_VERCEL = bool(os.environ.get("VERCEL"))
_DEFAULT_HOME = Path("/tmp/bookforge") if ON_VERCEL else Path.home() / ".bookforge"
PATH = Path(os.environ.get("BOOKFORGE_HOME", _DEFAULT_HOME)) / "settings.json"
SECRETS = ("openai_api_key", "anthropic_api_key")
# settings an account may not change: they point at the server's own disk
SERVER_ONLY = ("books_dir", "realesrgan_path")
# the signed-in account of the current request (None: the single-user studio on this computer)
current_user: contextvars.ContextVar[str | None] = contextvars.ContextVar("bookforge_user", default=None)


def user_id(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def home() -> Path:
    """The folder for this studio's (or this account's) files: books, characters, spend log."""
    u = current_user.get()
    return PATH.parent / "users" / user_id(u) if u else PATH.parent


def spend_path() -> Path:  # every paid image: when, estimated USD, book, slot
    return home() / "spend.json"
BUY_CREDITS_URL = "https://platform.openai.com/settings/organization/billing/overview"
_spend_lock = threading.Lock()


class Settings(BaseModel):
    openai_api_key: str = ""
    anthropic_api_key: str = ""   # optional: when empty, Claude runs on the Claude Code login
    claude_model: str = "claude-opus-5-5"
    books_dir: str = str(Path("/tmp/bookforge/books") if ON_VERCEL else Path.cwd() / "books")
    default_author: str = ""
    default_trim: str = "8.5x8.5"
    default_paper: str = "premium_color"
    # copied into the images: block of every new book.yaml
    image_model: str = "gpt-image-2.5-sunburst"
    image_quality: str = "medium"
    review: bool = True
    est_cost_per_image_usd: float = 0.05
    max_workers: int = 4
    realesrgan_path: str = ""
    # OpenAI has no API for the prepaid balance: you type it from the billing page, and MosiBooks subtracts
    # the estimated cost of every image generated since
    openai_credit_usd: float = 0.0
    openai_credit_set_at: float = 0.0
    voice_lang: str = "fa-IR"     # speech-recognition language of the voice buttons
    onboarded: bool = False       # finished (or skipped) the first-run setup wizard

    def image_block(self) -> dict:
        return {"model": self.image_model, "quality": self.image_quality, "review": self.review,
                "est_cost_per_image_usd": self.est_cost_per_image_usd,
                "max_workers": self.max_workers, "text_in_art": True}

    def masked(self) -> dict:
        d = self.model_dump()
        for k in SECRETS:
            v = d[k]
            d[k] = f"{v[:3]}…{v[-4:]}" if len(v) > 10 else ("set" if v else "")
        return d

    def apply_env(self) -> None:
        """Export keys for the OpenAI client, the Claude Agent SDK and the upscaler."""
        for key, env in (("openai_api_key", "OPENAI_API_KEY"), ("anthropic_api_key", "ANTHROPIC_API_KEY"),
                         ("realesrgan_path", "BOOKFORGE_REALESRGAN")):
            if getattr(self, key):
                os.environ[env] = getattr(self, key)
            elif key == "anthropic_api_key":
                os.environ.pop(env, None)  # fall back to the Claude Code login


def load() -> Settings:
    if u := current_user.get():
        from . import kv
        data = kv.get(f"settings:{user_id(u)}") or {}
        data.update(books_dir=str(home() / "books"), realesrgan_path="")
        return Settings.model_validate(data)
    return Settings.model_validate_json(PATH.read_text()) if PATH.exists() else Settings()


def save(updates: dict) -> Settings:
    """Merge `updates` into the stored settings. Masked secrets sent back unchanged are ignored."""
    current = load().model_dump()
    masked = load().masked()
    for k, v in updates.items():
        if k in SECRETS and v == masked[k]:
            continue
        if k in SERVER_ONLY and current_user.get():
            continue
        if k == "openai_credit_usd" and float(v or 0) != current[k]:
            current["openai_credit_set_at"] = time.time()  # a new balance: count spending from now
        current[k] = v
    s = Settings.model_validate(current)
    if s.default_trim not in kdp.TRIMS:
        raise ValueError(f"trim {s.default_trim!r} not a KDP size")
    if u := current_user.get():
        from . import kv
        kv.set(f"settings:{user_id(u)}", s.model_dump(exclude=set(SERVER_ONLY)))
        return s  # keys are passed to each client explicitly, never through the shared environment
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(s.model_dump(), indent=2))
    PATH.chmod(0o600)
    s.apply_env()
    return s


def openai_key() -> str | None:
    """This studio's (or account's) OpenAI key; None lets the client read OPENAI_API_KEY."""
    return load().openai_api_key or None


def record_spend(usd: float, book: str, slot: str) -> None:
    """Log one paid image (estimated cost) for the credit balance in Settings."""
    with _spend_lock:
        f = spend_path()
        entries = json.loads(f.read_text()) if f.exists() else []
        entries.append({"t": time.time(), "usd": round(usd, 4), "book": book, "slot": slot})
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(entries))


def credit() -> dict:
    """The OpenAI balance you entered, minus the estimated cost of the images generated since."""
    s = load()
    f = spend_path()
    entries = json.loads(f.read_text()) if f.exists() else []
    spent = sum(e["usd"] for e in entries if e["t"] >= s.openai_credit_set_at)
    return {"balance": s.openai_credit_usd, "set_at": s.openai_credit_set_at, "spent": round(spent, 2),
            "images": sum(1 for e in entries if e["t"] >= s.openai_credit_set_at),
            "remaining": round(s.openai_credit_usd - spent, 2) if s.openai_credit_usd else None,
            "buy_url": BUY_CREDITS_URL}
