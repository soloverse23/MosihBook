"""Self-update for the Windows install (packaging/windows).

The app asks GitHub for the latest release of REPO. When it is newer than the installed version, the page
offers it; on "Update now" the app downloads the release's MosiBooks-Update.zip, unpacks it next to the
install, starts its Install-MosiBooks.bat in update mode and exits. The installer waits for the app to
stop, installs the new files, and starts the app again; the open page reloads when it is back.

Only on when MosiBooks.bat started the app (it sets MOSIBOOKS_APP_DIR), so dev runs and Vercel never
update themselves.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

REPO = os.environ.get("MOSIBOOKS_UPDATE_REPO", "soloverse23/MosihBook")
ASSET = "MosiBooks-Update.zip"
CHECK_EVERY = 3600

_cache: tuple[float, dict] | None = None
_applying = False


def app_dir() -> Path | None:
    d = os.environ.get("MOSIBOOKS_APP_DIR")
    return Path(d) if d and os.name == "nt" else None


def current() -> str:
    try:
        return version("bookforge")
    except PackageNotFoundError:
        return "0"


def parse(v: str) -> tuple[int, ...]:
    out = []
    for part in v.strip().lstrip("vV").split("."):
        digits = "".join(c for c in part if c.isdigit())
        out.append(int(digits or 0))
    return tuple(out)


def newer(latest: str, installed: str) -> bool:
    a, b = parse(latest), parse(installed)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def _ctx() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _get(url: str, timeout: float = 15):
    req = urllib.request.Request(url, headers={"User-Agent": "MosiBooks-updater",
                                               "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout, context=_ctx())


def latest_release() -> dict | None:
    """The newest published release that carries the update ZIP, or None."""
    try:
        with _get(f"https://api.github.com/repos/{REPO}/releases/latest") as r:
            rel = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # nothing released yet
            return None
        raise
    asset = next((a for a in rel.get("assets", []) if a.get("name") == ASSET), None)
    if not asset:
        return None
    digest = asset.get("digest") or ""
    return {"version": rel.get("tag_name", "").lstrip("vV"), "notes": rel.get("body") or "",
            "url": asset["browser_download_url"], "size": asset.get("size", 0),
            "sha256": digest.split(":", 1)[1] if digest.startswith("sha256:") else ""}


def check(force: bool = False) -> dict:
    global _cache
    info = {"enabled": app_dir() is not None, "current": current(), "available": False}
    if not info["enabled"]:
        return info
    if not force and _cache and time.time() - _cache[0] < CHECK_EVERY:
        return {**info, **_cache[1]}
    try:
        rel = latest_release()
    except Exception as e:  # offline, rate-limited: try again on the next check
        return {**info, "error": str(e)}
    found = {"available": bool(rel and newer(rel["version"], info["current"])),
             "latest": rel["version"] if rel else None, "notes": rel["notes"] if rel else "", "_rel": rel}
    _cache = (time.time(), found)
    return {**info, **found}


def public(info: dict) -> dict:
    return {k: v for k, v in info.items() if not k.startswith("_")}


def apply() -> str:
    """Download and unpack the update, start its installer, and stop this server. Returns the new version."""
    global _applying
    base = app_dir()
    if base is None:
        raise RuntimeError("Updates only work in the installed Windows app")
    if _applying:
        raise RuntimeError("The update is already being installed")
    info = check(force=True)
    rel = info.get("_rel")
    if not info.get("available") or not rel:
        raise RuntimeError(info.get("error") or "You already have the newest version")
    _applying = True
    try:
        work = base / "update"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        zpath = work / ASSET
        h = hashlib.sha256()
        with _get(rel["url"], timeout=60) as r, open(zpath, "wb") as f:
            while chunk := r.read(1 << 20):
                h.update(chunk)
                f.write(chunk)
        if rel["sha256"] and h.hexdigest() != rel["sha256"]:
            raise RuntimeError("The download was damaged. Try again.")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(work / "new")
        installer = next((work / "new").glob("*/Install-MosiBooks.bat"), None)
        if not installer or not (installer.parent / "payload" / "uv.exe").exists():
            raise RuntimeError("The update package is incomplete")
    except Exception:
        _applying = False
        raise
    # its own window, so it outlives this process; the installer waits for the port to free up
    subprocess.Popen(["cmd", "/c", "start", "MosiBooks update", "/min", str(installer), "update"],
                     cwd=str(installer.parent), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    threading.Timer(1.5, os._exit, (0,)).start()  # after the response reaches the page
    return rel["version"]
