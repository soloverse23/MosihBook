"""AI upscaling with Real-ESRGAN when installed, Lanczos otherwise.

Install the binary from https://github.com/xinntao/Real-ESRGAN/releases (realesrgan-ncnn-vulkan,
macOS build) and put it on PATH or set BOOKFORGE_REALESRGAN to its path.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path

from PIL import Image


REPO_BINARY = Path(__file__).resolve().parents[2] / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan"


def _binary() -> str | None:
    found = os.environ.get("BOOKFORGE_REALESRGAN") or shutil.which("realesrgan-ncnn-vulkan")
    return found or (str(REPO_BINARY) if REPO_BINARY.exists() else None)


def upscale(im: Image.Image, factor: float) -> Image.Image:
    exe = _binary()
    if exe and factor > 1.15:
        scale = 4 if factor > 2 else 2
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, "in.png"), Path(tmp, "out.png")
            im.save(src)
            models = Path(exe).resolve().parent / "models"
            subprocess.run([exe, "-i", str(src), "-o", str(dst), "-s", str(scale),
                            *(["-m", str(models)] if models.is_dir() else []),
                            "-n", "realesrgan-x4plus" if scale == 4 else "realesr-animevideov3"],
                           check=True, capture_output=True)
            with Image.open(dst) as out:
                return out.convert("RGB")
    if factor > 1.5 and not exe:
        warnings.warn(f"upscaling {factor:.1f}x with Lanczos; install Real-ESRGAN for sharper print art")
    return im.resize((round(im.width * factor), round(im.height * factor)), Image.LANCZOS)
