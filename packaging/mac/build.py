#!/usr/bin/env python3
"""Mac packaging for MosiBooks: a double-click local install for one person (Apple Silicon and Intel).

    python packaging/mac/build.py              # dist/MosiBooks-Mac.zip
    python packaging/mac/build.py --out ~/Desktop/MosiBooks-Mac.zip

Uses the same login as the Windows build (dist/login.txt). The Mac install does not self-update yet:
a new version is installed by running a new ZIP over the old one; books and settings are kept.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "windows"))
from build import DIST, LOGIN, ROOT, USERNAME, app_files, pyproject_version, run, saved_password  # noqa: E402

UV_VERSION = "0.13.7"
UV_SHA256 = {"aarch64": "81b811b57e4624df7ed3aac148e0359100d9962f3d9dce00aec533dc2e086731",
             "x86_64": "20c47e4c1f630b8abaff8c291fa9b9aa300fef92c4fbff95adf198b55287cda7"}


def uv_bin(arch: str) -> bytes:
    cached = DIST / f"uv-{UV_VERSION}-{arch}-apple-darwin.tar.gz"
    if not cached.exists():
        url = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-{arch}-apple-darwin.tar.gz"
        subprocess.run(["curl", "-fsSL", "-o", str(cached), url], check=True)
    data = cached.read_bytes()
    if hashlib.sha256(data).hexdigest() != UV_SHA256[arch]:
        cached.unlink()
        raise SystemExit("uv download failed its checksum")
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        return t.extractfile(next(m for m in t.getmembers() if m.name.endswith("/uv"))).read()


def mac_lock() -> str:
    return run("uv", "pip", "compile", "pyproject.toml", "--extra", "web", "--python-platform", "macos",
               "--python-version", "3.12", "--no-header", "--no-annotate", "-q")


def put(z: zipfile.ZipFile, name: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 if executable else 0o100644) << 16
    z.writestr(info, data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DIST / "MosiBooks-Mac.zip")
    args = ap.parse_args()
    password = saved_password()
    if not password:
        raise SystemExit("no dist/login.txt: run packaging/windows/build.py once to make the login")
    DIST.mkdir(exist_ok=True)
    base = "MosiBooks"
    out = args.out.expanduser()
    with zipfile.ZipFile(out, "w") as z:
        for name in ("Install-MosiBooks.command", "Stop-MosiBooks.command"):
            put(z, f"{base}/{name}", (HERE / name).read_bytes(), executable=True)
        put(z, f"{base}/README-FA.txt", (HERE / "README-FA.txt").read_bytes())
        for name in ("MosiBooks.sh", "Claude-Login.command"):
            put(z, f"{base}/payload/{name}", (HERE / name).read_bytes(), executable=True)
        put(z, f"{base}/payload/credentials.sh",
            f"export MOSIBOOKS_USER='{USERNAME}'\nexport MOSIBOOKS_PASSWORD='{password}'\n".encode())
        put(z, f"{base}/payload/requirements.lock", mac_lock().encode())
        put(z, f"{base}/payload/uv-arm64", uv_bin("aarch64"), executable=True)
        put(z, f"{base}/payload/uv-x86_64", uv_bin("x86_64"), executable=True)
        for f in app_files():
            put(z, f"{base}/payload/app/{f}", (ROOT / f).read_bytes())
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB), version {pyproject_version()}\n"
          f"username: {USERNAME}\npassword: {password}")


if __name__ == "__main__":
    main()
