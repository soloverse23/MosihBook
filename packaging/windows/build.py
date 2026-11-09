#!/usr/bin/env python3
"""Windows packaging for MosiBooks: a double-click local install for one person, then self-updates.

    python packaging/windows/build.py                     # dist/MosiBooks-Windows.zip, the first install
    python packaging/windows/build.py --new-password      # same, with a fresh random password
    python packaging/windows/build.py release "notes"     # publish an update the installed app offers

The first-install ZIP carries the login (credentials.bat). The password is kept in dist/login.txt and
reused on every build, so a reinstall never changes it; it never goes into the repo or a release.

`release` bumps the patch version in pyproject.toml (or uses --version), commits and pushes that, builds
dist/MosiBooks-Update.zip (no login inside) and publishes it as a GitHub release of the public repo. The
installed app checks for that release, shows a popup, and installs it on one click (bookforge/web/updater.py).
Commit your changes first: a release is built only from committed files.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import secrets
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIST = ROOT / "dist"
LOGIN = DIST / "login.txt"
UV_VERSION = "0.13.7"
UV_SHA256 = "0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021"
UV_URL = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
USERNAME = "mosibooks"
ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # also safe inside a .bat `set`
UPDATE_ASSET = "MosiBooks-Update.zip"  # must match bookforge/web/updater.py ASSET
VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.M)


def run(*cmd: str, **kw) -> str:
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, **kw).stdout.strip()


def crlf(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode()


def uv_exe() -> bytes:
    cached = DIST / f"uv-{UV_VERSION}-windows.zip"
    if not cached.exists():
        subprocess.run(["curl", "-fsSL", "-o", str(cached), UV_URL], check=True)
    data = cached.read_bytes()
    if hashlib.sha256(data).hexdigest() != UV_SHA256:
        cached.unlink()
        raise SystemExit("uv download failed its checksum")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read(next(n for n in z.namelist() if n.endswith("uv.exe")))


def windows_lock() -> str:
    return run("uv", "pip", "compile", "pyproject.toml", "--extra", "web", "--python-platform", "windows",
               "--python-version", "3.12", "--no-header", "--no-annotate", "-q")


def app_files() -> list[str]:
    return [f for f in run("git", "ls-files", "bookforge", "pyproject.toml", "README.md").split("\n") if f]


def pyproject_version() -> str:
    return VERSION_LINE.search((ROOT / "pyproject.toml").read_text()).group(1)


def build_zip(out: Path, password: str | None) -> Path:
    """The installer folder; with a password it is a first install, without one an update."""
    DIST.mkdir(exist_ok=True)
    base = "MosiBooks"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}/Install-MosiBooks.bat", crlf((HERE / "Install-MosiBooks.bat").read_text()))
        z.writestr(f"{base}/README-FA.txt", b"\xef\xbb\xbf" + crlf((HERE / "README-FA.txt").read_text(encoding="utf-8")).decode().encode("utf-8"))
        for name in ("MosiBooks.bat", "Claude-Login.bat"):
            z.writestr(f"{base}/payload/{name}", crlf((HERE / name).read_text()))
        if password:
            z.writestr(f"{base}/payload/credentials.bat",
                       crlf(f"@set \"MOSIBOOKS_USER={USERNAME}\"\n@set \"MOSIBOOKS_PASSWORD={password}\"\n"))
        z.writestr(f"{base}/payload/requirements.lock", windows_lock())
        z.writestr(f"{base}/payload/uv.exe", uv_exe())
        for f in app_files():
            z.write(ROOT / f, f"{base}/payload/app/{f}")
    return out


def saved_password() -> str | None:
    if LOGIN.exists():
        m = re.search(r"^password: (\S+)$", LOGIN.read_text(), re.M)
        return m.group(1) if m else None
    return None


def install(args) -> None:
    password = args.password or (None if args.new_password else saved_password()) \
        or "".join(secrets.choice(ALPHABET) for _ in range(16))
    if not password.isalnum():
        raise SystemExit("use letters and digits only: the password is written into a .bat file")
    out = build_zip(DIST / "MosiBooks-Windows.zip", password)
    LOGIN.write_text(f"username: {USERNAME}\npassword: {password}\n")
    LOGIN.chmod(0o600)
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB), version {pyproject_version()}\n"
          f"username: {USERNAME}\npassword: {password}")


def bump(v: str) -> str:
    parts = [int(p) for p in v.split(".")]
    parts[-1] += 1
    return ".".join(map(str, parts))


def release(args) -> None:
    dirty = run("git", "status", "--porcelain", "--", "bookforge", "pyproject.toml", "README.md", "packaging")
    if dirty:
        raise SystemExit(f"Commit these first, a release is built only from committed files:\n{dirty}")
    repo = run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    old = pyproject_version()
    new = args.version or bump(old)
    if new == old or subprocess.run(["gh", "release", "view", f"v{new}"], cwd=ROOT,
                                    capture_output=True).returncode == 0:
        raise SystemExit(f"v{new} is already released or not newer than {old}; pass a higher --version")

    py = ROOT / "pyproject.toml"
    before = py.read_text()
    py.write_text(VERSION_LINE.sub(f'version = "{new}"', before, count=1))
    try:
        out = build_zip(DIST / UPDATE_ASSET, password=None)
    except BaseException:
        py.write_text(before)
        raise
    run("git", "add", "pyproject.toml")
    run("git", "commit", "-m", f"Release v{new}")
    run("git", "push", "origin", "HEAD")
    sha = run("git", "rev-parse", "HEAD")
    notes = args.notes or f"MosiBooks {new}"
    subprocess.run(["gh", "release", "create", f"v{new}", str(out), "--repo", repo, "--target", sha,
                    "--title", f"MosiBooks {new}", "--notes", notes], cwd=ROOT, check=True)
    print(f"Released v{new} ({out.stat().st_size / 1e6:.1f} MB). Installed apps offer it the next time they open.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    ap.add_argument("--password", help="letters and digits; default: the one in dist/login.txt")
    ap.add_argument("--new-password", action="store_true", help="make a fresh random password")
    rel = sub.add_parser("release", help="publish an update for installed apps")
    rel.add_argument("notes", nargs="?", default="", help="what changed; shown in the update popup")
    rel.add_argument("--version", help="default: bump the last number of the version in pyproject.toml")
    args = ap.parse_args()
    (release if args.cmd == "release" else install)(args)


if __name__ == "__main__":
    main()
