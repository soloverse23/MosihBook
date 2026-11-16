"""Redraw a page picture so its words sit inside the safe margin.

Words the image model letters into a picture often run to its edge, where the trim may cut them. To fix a
page, the current picture is shrunk into the page's live area (kdp.Interior.art_live_box: 9.7 mm from the
trim, gutter and bleed accounted for) on a page-shaped draft, its outer band only a soft blur of the picture.
That draft goes to the image model as the layout of the page, and the model draws the whole page again as one
new picture: same scene, characters and words, every letter where the draft has it, inside the margin.
Nothing of the old picture is pasted back, so there is no seam.

The first redraw keeps the untouched picture in build/art-originals/ and drafts always start from it, so a
second redraw is not a copy of a copy. A Redo without the margin option drops it.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageFilter

from .. import kdp
from ..project import Project

DRAFT_ROLE = ("layout draft of THIS page, made from its previous picture. Redraw it as one finished full-bleed "
              "illustration: keep the same scene, characters, poses and every word where the draft has them, "
              "at the same size. The draft's soft blurred outer band is only a placeholder: paint it as real "
              "scenery that continues the picture to every edge, with no words, faces or important details in "
              "it. Do not copy the blur, and do not add a frame or border.")
MARGIN_NOTE = ("Every letter, and every face, stays inside the sharp middle area of the layout draft, never in its "
               "blurred outer band: the page is trimmed there and words near the edge get cut.")

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


def forget(project: Project, slot_id: str) -> None:
    """A new picture replaced this slot's art (a Redo): its kept original no longer applies."""
    (project.build / "art-originals" / f"{slot_id}.png").unlink(missing_ok=True)
    f = _store_path(project)  # left by the border-only fit of v0.1.13
    if f.exists() and slot_id in (data := json.loads(f.read_text())):
        data.pop(slot_id)
        f.write_text(json.dumps(data, indent=2))


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


def _canvas(orig: Image.Image, box: list[float], live: list[float]) -> Image.Image:
    """The page at box aspect with the picture contained in the live area, its outer band a soft blur of it."""
    bx, by, bw, bh = box
    lx, ly, lw, lh = live
    # live area as fractions of the box, top-left origin (the PDF counts from the bottom)
    fx, fy = (lx - bx) / bw, (by + bh - (ly + lh)) / bh
    fw, fh = lw / bw, lh / bh
    ow, oh = orig.size
    aspect = bw / bh
    W = max(ow / fw, oh / fh * aspect)
    W, H = round(W), round(W / aspect)
    lpx, lpy, lpw, lph = fx * W, fy * H, fw * W, fh * H
    px, py = round(lpx + (lpw - ow) / 2), round(lpy + (lph - oh) / 2)
    canvas = orig.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(W, H) / 60))
    canvas.paste(orig, (px, py))
    return canvas


def draft(project: Project, slot_id: str) -> Path | None:
    """Write the layout draft for redrawing a slot inside the margin; None when it cannot be made (no picture,
    not a single-page picture in the last build, or already inside the live area)."""
    p = placement(project, slot_id)
    art = project.art_path(slot_id)
    if p is None or not needs_fit(p) or not art.exists():
        return None
    orig_path = originals_dir(project) / f"{slot_id}.png"
    if not orig_path.exists():
        shutil.copyfile(art, orig_path)
    with Image.open(orig_path) as im:
        canvas = _canvas(im.convert("RGB"), p["box"], p["live"])
    out = project.build / "margin-drafts" / f"{slot_id}.png"
    out.parent.mkdir(exist_ok=True)
    canvas.save(out, "PNG")
    return out
