"""Stage 4: crop art to its exact printed box and bring it to 300 DPI."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps

from .. import kdp
from .upscale import upscale


def _crop_to_aspect(im: Image.Image, aspect: float) -> Image.Image:
    if im.width / im.height > aspect:
        nw = round(im.height * aspect)
        x = (im.width - nw) // 2
        return im.crop((x, 0, x + nw, im.height))
    nh = round(im.width / aspect)
    y = (im.height - nh) // 2
    return im.crop((0, y, im.width, y + nh))


def prepare(src: Path, w_in: float, h_in: float, out_dir: Path,
            crop: tuple[float, float] | None = None) -> tuple[Path, float]:
    """Cover-fit `src` to a w_in x h_in box, output at exactly 300 DPI.

    Returns (jpeg path, native DPI of the source art before any upscaling) - the honest number
    for preflight. `crop` keeps a horizontal slice (fractions) after fitting, used to cut a
    spread into its two pages.
    """
    with Image.open(src) as probe:
        sw, sh = probe.size
    aspect = w_in / h_in
    native_w = min(sw, sh * aspect)
    native_dpi = native_w / w_in

    tag = hashlib.sha256(f"{src}{src.stat().st_mtime_ns}{w_in:.4f}{h_in:.4f}{crop}".encode()).hexdigest()[:16]
    out = out_dir / f"{src.stem}-{tag}.jpg"
    if out.exists():
        return out, native_dpi

    with Image.open(src) as im:
        im = _crop_to_aspect(ImageOps.exif_transpose(im).convert("RGB"), aspect)
    target = (round(w_in * kdp.MIN_DPI), round(h_in * kdp.MIN_DPI))
    if im.width < target[0]:
        im = upscale(im, target[0] / im.width)
    im = im.resize(target, Image.LANCZOS)
    if crop:
        im = im.crop((round(im.width * crop[0]), 0, round(im.width * crop[1]), im.height))
    im.save(out, "JPEG", quality=93, dpi=(kdp.MIN_DPI, kdp.MIN_DPI), subsampling=0)
    return out, native_dpi


def soften(path: Path, paper: str, out_dir: Path, edge: float = 0.1) -> Path:
    """A vignette on the page's paper: its white background takes the paper's color (a multiply, so the
    picture keeps its colors) and its edges fade out, so it never sits on the page as a white box."""
    from PIL import ImageChops, ImageFilter
    tag = hashlib.sha256(f"{path}{path.stat().st_mtime_ns}{paper}{edge}".encode()).hexdigest()[:16]
    out = out_dir / f"{path.stem}-soft-{tag}.png"
    if out.exists():
        return out
    with Image.open(path) as im:
        im = im.convert("RGB")
    tint = Image.new("RGB", im.size, paper)
    im = ImageChops.multiply(im, tint)
    w, h = im.size
    m = max(2, round(min(w, h) * edge))
    mask = Image.new("L", (w, h), 0)
    mask.paste(255, (m, m, w - m, h - m))
    mask = mask.filter(ImageFilter.GaussianBlur(m / 2))
    im.putalpha(mask)
    im.save(out, "PNG", dpi=(kdp.MIN_DPI, kdp.MIN_DPI))
    return out


def melt_bottom(path: Path, paper: str, out_dir: Path, share: float = 0.34) -> Path:
    """A banner whose lower `share` dissolves smoothly into the page's paper (a baked gradient: no stripes,
    no overlay), so the words under it sit on plain paper."""
    from PIL import ImageFilter
    tag = hashlib.sha256(f"{path}{path.stat().st_mtime_ns}{paper}{share}".encode()).hexdigest()[:16]
    out = out_dir / f"{path.stem}-melt-{tag}.jpg"
    if out.exists():
        return out
    with Image.open(path) as im:
        im = im.convert("RGB")
    w, h = im.size
    start = h * (1 - share)
    ramp = Image.new("L", (1, h), 0)
    for y in range(h):
        t = min(1.0, max(0.0, (y - start) / (h - start)))
        ramp.putpixel((0, y), round(255 * t * t * (3 - 2 * t)))  # smoothstep
    mask = ramp.resize((w, h))
    im = Image.composite(Image.new("RGB", (w, h), paper), im, mask)
    im.save(out, "JPEG", quality=93, dpi=(kdp.MIN_DPI, kdp.MIN_DPI), subsampling=0)
    return out
