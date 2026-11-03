"""Stage 6: KDP wraparound cover (back | spine | front) sized from the real interior page count."""
from __future__ import annotations

import json

from PIL import Image, ImageFilter, ImageStat
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

from .. import kdp
from ..project import Project
from .base import Sheet, para_html, theme_for


def _palette_from(src) -> tuple[str, str]:
    """(dark spine color, readable text color) sampled from the front art."""
    with Image.open(src) as im:
        r, g, b = (int(v) for v in ImageStat.Stat(im.convert("RGB").resize((64, 64))).mean)
    dark = "#%02x%02x%02x" % (int(r * 0.55), int(g * 0.55), int(b * 0.55))
    return dark, "#FFFFFF"


def _back_art(project: Project, front) -> "Path":
    """Mirrored, heavily blurred front art: a calm back cover that matches the front."""
    out = project.prepared / "cover-back-derived.png"
    if not out.exists() or out.stat().st_mtime < front.stat().st_mtime:
        with Image.open(front) as im:
            im = im.convert("RGB").transpose(Image.FLIP_LEFT_RIGHT)
            size = im.size
            im = im.resize((im.width // 4, im.height // 4)).filter(ImageFilter.GaussianBlur(18))
            im.resize(size, Image.BICUBIC).save(out)  # blur hides no detail, so plain resampling is fine
    return out


def _scrim(project: Project, front) -> "Path":
    """Front art with a soft dark gradient under the title zone so white type always reads."""
    out = project.prepared / "cover-front-scrim.png"
    if not out.exists() or out.stat().st_mtime < front.stat().st_mtime:
        with Image.open(front) as im:
            im = im.convert("RGB")
            mask = Image.linear_gradient("L").rotate(180).resize(im.size)  # 255 at top -> 0 at bottom
            mask = mask.point(lambda v: max(0, v - 120) * 0.95)             # only the top ~45%, max ~50%
            im.paste((12, 14, 28), mask=mask)
            im.save(out)
    return out


def _title_lines(sheet: Sheet, text: str, font: str, max_w: float, max_size: float) -> tuple[list[str], float]:
    words, size = text.split(), max_size
    while size > 14:
        lines, cur = [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if sheet.c.stringWidth(trial, font, size) / inch <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 3 and all(sheet.c.stringWidth(l, font, size) / inch <= max_w for l in lines):
            return lines, size
        size -= 2
    return lines, size


def _shadowed(sheet: Sheet, x: float, y: float, s: str, font: str, size: float, color: str) -> None:
    c = sheet.c
    c.setFont(font, size)
    c.setFillColor(Color(0, 0, 0, alpha=0.45))
    c.drawCentredString((x + size / 72 * 0.05) * inch, (y - size / 72 * 0.05) * inch, s)
    c.setFillColor(HexColor(color))
    c.drawCentredString(x * inch, y * inch, s)


def build_cover(project: Project) -> dict:
    book = project.book
    if not project.manifest.exists():
        raise FileNotFoundError("build the interior first - the spine width depends on its page count")
    pages = json.loads(project.manifest.read_text())["pages"]
    tw, th = book.trim_size
    cov = kdp.Cover(tw, th, pages, book.paper)
    theme = theme_for(book)
    sheet = Sheet(project.cover_pdf, (cov.width, cov.height), project.prepared, theme)
    front = project.art_path("cover-front")
    back = project.art_path("cover-back")
    spine_color, ink = _palette_from(front)
    lettered = book.images.text_in_art  # title, author and blurb are lettered into the art itself

    # art: front panel (incl. right bleed), back panel (incl. left bleed), solid spine
    sheet.image(front if lettered else _scrim(project, front), (cov.front_x, 0, tw + kdp.BLEED, cov.height))
    sheet.image(back if back.exists() else _back_art(project, front), (0, 0, kdp.BLEED + tw, cov.height))
    sheet.fill(spine_color, (cov.spine_x, 0, cov.spine, cov.height))

    if lettered:
        _spine(sheet, cov, book, theme, ink, th)
        return _finish(project, sheet, cov, pages, book)

    # front: title in the calm top area, author at the bottom
    fx = cov.front_x + kdp.SAFE
    fw = tw - 2 * kdp.SAFE
    top = kdp.BLEED + th - kdp.SAFE
    lines, size = _title_lines(sheet, book.title, theme.heading, fw, 64)
    y = top - size / 72
    for line in lines:
        _shadowed(sheet, fx + fw / 2, y, line, theme.heading, size, ink)
        y -= size / 72 * 1.08
    if book.subtitle:
        _shadowed(sheet, fx + fw / 2, y - 0.1, book.subtitle, theme.body, max(12, size * 0.32), ink)
    _shadowed(sheet, fx + fw / 2, kdp.BLEED + kdp.SAFE + 0.1, book.author.upper(), theme.body_bold, 16, ink)
    sheet.records["text"].append({"page": 1, "box": [fx, kdp.BLEED + kdp.SAFE, fw, top - kdp.BLEED - kdp.SAFE],
                                  "safe": [fx, kdp.BLEED + kdp.SAFE, fw, th - 2 * kdp.SAFE]})

    # back: blurb panel above the reserved barcode box
    bx, by, bw, bh = cov.barcode_box()
    safe_back = (kdp.BLEED + kdp.SAFE, kdp.BLEED + kdp.SAFE, tw - 2 * kdp.SAFE, th - 2 * kdp.SAFE)
    if book.back_cover.blurb:
        area_y = by + bh + 0.35
        area = (safe_back[0], area_y, safe_back[2], safe_back[1] + safe_back[3] - area_y)
        sheet.text(para_html(book.back_cover.blurb), area, min(theme.size, 14), valign="top", panel=True,
                   safe=safe_back, align=TA_LEFT if book.type == "storybook" else TA_CENTER)

    _spine(sheet, cov, book, theme, ink, th)
    return _finish(project, sheet, cov, pages, book)


def _spine(sheet, cov, book, theme, ink, th) -> None:
    """Spine text only when KDP allows it."""
    if cov.spine_text_allowed:
        c = sheet.c
        room = cov.spine - 2 * kdp.SPINE_TEXT_MARGIN
        fs = min(18, room * 72 * 0.62)
        c.saveState()
        c.translate((cov.spine_x + cov.spine / 2) * inch, (cov.height / 2) * inch)
        c.rotate(-90)
        c.setFillColor(HexColor(ink))
        c.setFont(theme.heading, fs)
        c.drawCentredString(-0.6 * inch, -fs * 0.35, book.title)
        c.setFont(theme.body, fs * 0.7)
        c.drawString((th / 2 - kdp.SAFE - 1.6) * inch, -fs * 0.3, book.author)
        c.restoreState()


def _finish(project: Project, sheet: Sheet, cov, pages: int, book) -> dict:
    sheet.save()
    info = {"pages": pages, "paper": book.paper, "spine_in": round(cov.spine, 4),
            "size_in": [round(cov.width, 4), round(cov.height, 4)], "spine_text": cov.spine_text_allowed,
            "barcode_box": [round(v, 4) for v in cov.barcode_box()], "text": sheet.records["text"],
            "images": sheet.records["images"]}
    (project.build / "cover.json").write_text(json.dumps(info, indent=2))
    return info
