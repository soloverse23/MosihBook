"""Fit a page picture inside the safe margin without redrawing it.

Words the image model letters into a picture often run to its edge, where the trim may cut them. Redrawing
the picture would change it; instead the picture is kept exactly as it is, shrunk so all of it (every letter
included) sits inside the page's live area (kdp.Interior.art_live_box: 9.7 mm from the trim, gutter and
bleed accounted for), and only the new border around it is painted by the image model, as scenery. The
original is pasted back over the middle afterwards, so its words and characters cannot change.

The first fit keeps the untouched picture in build/art-originals/; a refit always starts from it, and a
Redo (a new picture) drops it. build/margins.json lists the fitted pictures and the box they were fitted to.
"""
from __future__ import annotations

import io
import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageFilter

from .. import kdp, settings as app_settings
from ..project import Project

FEATHER = 0.004   # share of the picture's short side over which the original blends into the new border

EXTEND_PROMPT = (
    "Extend this illustration outward so it fills the whole page. The picture in the middle is finished: keep "
    "it exactly as it is (same scene, characters, colors and words). Paint only the empty border around it, "
    "continuing the scenery seamlessly to every edge in the same style, colors and light, so the page reads as "
    "one full-bleed illustration with no frame and no visible seam. The border carries only background "
    "(sky, ground, water, foliage, walls, texture): no words, letters or numbers, no faces, no new characters "
    "or objects.")

# a Redo note that asks only to keep things inside the margin (any of the studio's languages)
_MARGIN_WORDS = re.compile(
    r"margin|marge|\brand|safe.?(area|zone)|bleed|trim|edge|too close|cut off|"
    r"حاشیه|مارجین|لبه|کناره|بریده|برش", re.I)


def is_margin_request(note: str | None) -> bool:
    return bool(note and _MARGIN_WORDS.search(note))


def originals_dir(project: Project) -> Path:
    d = project.build / "art-originals"
    d.mkdir(exist_ok=True)
    return d


def _store_path(project: Project) -> Path:
    return project.build / ("margins-mock.json" if project.mock else "margins.json")


def fitted(project: Project) -> dict:
    f = _store_path(project)
    return json.loads(f.read_text()) if f.exists() else {}


def forget(project: Project, slot_id: str) -> None:
    """A new picture replaced this slot's art: its old original and fit no longer apply."""
    (project.build / "art-originals" / f"{slot_id}.png").unlink(missing_ok=True)
    data = fitted(project)
    if data.pop(slot_id, None) is not None:
        _store_path(project).write_text(json.dumps(data, indent=2))


def placement(project: Project, slot_id: str) -> dict | None:
    """Where the slot's picture is printed in the last build: {page, box, live} in inches, or None when it is
    not on an interior page, is cut across two pages (a spread) or the book was built before boxes were kept."""
    if not project.manifest.exists():
        return None
    m = json.loads(project.manifest.read_text())
    tw, th = project.book.trim_size
    interior = kdp.Interior(tw, th, m["pages"])
    name = project.art_path(slot_id).name
    for rec in m["images"]:
        if rec["src"] != name or not rec.get("box") or rec.get("crop"):
            continue
        bx, by, bw, bh = rec["box"]
        lx, ly, lw, lh = interior.art_live_box()
        x0, y0 = max(bx, lx), max(by, ly)
        x1, y1 = min(bx + bw, lx + lw), min(by + bh, ly + lh)
        if x1 <= x0 or y1 <= y0:
            return None
        return {"page": rec["page"], "box": [bx, by, bw, bh], "live": [x0, y0, x1 - x0, y1 - y0]}
    return None


def needs_fit(p: dict) -> bool:
    """Does the printed picture reach past the live area (so its edges could hold letters in the margin)?"""
    bx, by, bw, bh = p["box"]
    lx, ly, lw, lh = p["live"]
    return lx - bx > 1e-3 or ly - by > 1e-3 or (bx + bw) - (lx + lw) > 1e-3 or (by + bh) - (ly + lh) > 1e-3


def _canvas(orig: Image.Image, box: list[float], live: list[float]):
    """The page picture at box aspect with the original contained in the live area, its border prefilled with a
    soft stretch of the original. Returns (canvas, keep mask, paste position)."""
    bx, by, bw, bh = box
    lx, ly, lw, lh = live
    # live area as fractions of the box, top-left origin (the PDF counts from the bottom)
    fx, fy = (lx - bx) / bw, (by + bh - (ly + lh)) / bh
    fw, fh = lw / bw, lh / bh
    ow, oh = orig.size
    aspect = bw / bh
    # keep the original at its own pixels: the page grows around it
    W = max(ow / fw, oh / fh * aspect)
    W, H = round(W), round(W / aspect)
    lpx, lpy, lpw, lph = fx * W, fy * H, fw * W, fh * H
    px, py = round(lpx + (lpw - ow) / 2), round(lpy + (lph - oh) / 2)
    canvas = orig.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(W, H) / 60))
    canvas.paste(orig, (px, py))
    keep = Image.new("L", (W, H), 0)
    keep.paste(255, (px, py, px + ow, py + oh))
    return canvas, keep, (px, py)


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def fit(project: Project, slot_id: str, provider, log: Callable[[str], None] = print) -> str:
    """Fit one slot's picture inside the margin. Returns a short result for the job log."""
    p = placement(project, slot_id)
    if p is None:
        return "skipped: not a single-page picture in the last build (build the book first)"
    if not needs_fit(p):
        return "already inside the margin"
    art = project.art_path(slot_id)
    if not art.exists():
        return "skipped: no picture yet"
    orig_path = originals_dir(project) / f"{slot_id}.png"
    if not orig_path.exists():
        shutil.copyfile(art, orig_path)
    with Image.open(orig_path) as im:
        orig = im.convert("RGB")
    canvas, keep, (px, py) = _canvas(orig, p["box"], p["live"])
    W, H = canvas.size

    settings = project.book.images
    size = provider.request_size(W / H)
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask.putalpha(keep)  # alpha 255 = keep, 0 = paint
    prompt = f"{EXTEND_PROMPT}\nART STYLE: {project.book.style.strip()}"
    out = provider.extend(_png(canvas.resize(size, Image.LANCZOS)), _png(mask.resize(size, Image.NEAREST)),
                          prompt, size, settings.quality_for(slot_id))
    if not project.mock:
        app_settings.record_spend(settings.cost(slot_id), project.root.name, f"{slot_id}-margin")
    with Image.open(io.BytesIO(out)) as im:
        page = im.convert("RGB").resize((W, H), Image.LANCZOS)

    # the original goes back on top; only its outermost pixels blend into the painted border
    f = max(2, round(min(orig.size) * FEATHER))
    blend = Image.new("L", (W, H), 0)
    blend.paste(255, (px + f, py + f, px + orig.width - f, py + orig.height - f))
    blend = blend.filter(ImageFilter.GaussianBlur(f / 2))
    page.paste(canvas, (0, 0), blend)
    tmp = art.with_suffix(".part.png")
    page.save(tmp, "PNG")
    tmp.replace(art)

    data = fitted(project)
    data[slot_id] = {"page": p["page"], "box": p["box"], "live": p["live"], "size": [W, H]}
    _store_path(project).write_text(json.dumps(data, indent=2))
    return f"fitted inside the {kdp.SAFE * 25.4:.1f} mm margin (picture kept, border extended)"

