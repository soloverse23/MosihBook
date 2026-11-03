"""Comic interiors: panel grids with bordered art, speech/thought balloons and captions."""
from __future__ import annotations

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

from .. import kdp
from ..project import Project
from ..spec import Bubble
from . import front_matter as fm
from .base import Sheet, para_html
from .geometry import Box, panel_boxes
from .picture_book import Draw

CAPTION_FILL = "#FFF3B0"
BUBBLE_PAD = 0.09


def sequence(project: Project) -> list[Draw]:
    book = project.book
    pages: list[Draw] = [lambda s, i: fm.title_page(s, i, book, project.art_path("cover-front")), lambda s, i: fm.copyright_page(s, i, book)]
    if book.front_matter.dedication:
        pages.append(lambda s, i: fm.dedication_page(s, i, book))
    for n, p in enumerate(book.pages, 1):
        if p.panels:
            srcs = [project.art_path(f"p{n:03d}-{k}") for k in range(1, len(p.panels) + 1)]
            pages.append(lambda s, i, p=p, srcs=srcs: _panel_page(s, i, p, srcs))
        else:
            src = project.art_path(f"p{n:03d}")
            pages.append(lambda s, i, p=p, src=src: _splash(s, i, p, src))
    closing = [lambda s, i: fm.the_end_page(s, i, book)]
    if book.about_author:
        closing.append(lambda s, i: fm.about_page(s, i, book))
    total = kdp.pad_page_count(len(pages) + len(closing))
    pages += [lambda s, i: fm.blank_page(s, i, book)] * (total - len(pages) - len(closing))
    return pages + closing


def _splash(sheet: Sheet, interior: kdp.Interior, page, src) -> None:
    sheet.image(src, (0, 0, interior.page_w, interior.page_h))
    if page.text:
        x, y, w, h = safe = interior.safe_box(sheet.page_no)
        _caption(sheet, para_html(page.text), (x, y, w * 0.7, h * 0.25), "bottom", safe)


def _panel_page(sheet: Sheet, interior: kdp.Interior, page, srcs) -> None:
    sheet.fill("#FFFFFF")
    safe = interior.safe_box(sheet.page_no)
    x, y, w, h = safe
    area = (x, y + 0.22, w, h - 0.22)  # leave room for the folio
    c = sheet.c
    for panel, src, box in zip(page.panels, srcs, panel_boxes(len(page.panels), area)):
        bx, by, bw, bh = box
        sheet.image(src, box)
        c.setStrokeColor(black)
        c.setLineWidth(2.2)
        c.rect(bx * inch, by * inch, bw * inch, bh * inch, stroke=1, fill=0)
        _bubbles(sheet, panel.bubbles, box, safe)
    sheet.folio(interior)


def _bubbles(sheet: Sheet, bubbles: list[Bubble], box: Box, safe: Box) -> None:
    bx, by, bw, bh = box
    stacks: dict[str, float] = {}
    for b in bubbles:
        corner = b.position
        top = corner.startswith("top")
        if b.kind == "caption":
            area_h = bh * 0.3
            area = (bx + 0.06, by + bh - 0.06 - area_h if top else by + 0.06, bw - 0.12, area_h)
            _caption(sheet, para_html(b.text), area, "top" if top else "bottom", safe, offset=stacks.get(corner, 0))
            stacks[corner] = stacks.get(corner, 0) + 0.45
            continue
        width = bw * (0.62 if corner in ("top", "bottom") else 0.48)
        html = para_html(b.text.upper())
        p, ph = sheet.fit_paragraph(html, width - 2 * BUBBLE_PAD, bh * 0.4, sheet.theme.size, min_size=7,
                                    align=TA_CENTER, leading=1.18)
        # shrink-wrap the balloon to the longest line
        pw = min(width, max(p.getActualLineWidths0()) / inch + 2 * BUBBLE_PAD + 0.04)
        p, ph = sheet.fit_paragraph(html, pw - 2 * BUBBLE_PAD, bh * 0.4, sheet.theme.size, min_size=7,
                                    align=TA_CENTER, leading=1.18)
        qh = ph + 2 * BUBBLE_PAD
        off = stacks.get(corner, 0)
        if corner.endswith("left"):
            qx = bx + 0.12
        elif corner.endswith("right"):
            qx = bx + bw - pw - 0.12
        else:
            qx = bx + (bw - pw) / 2
        qy = by + bh - qh - 0.12 - off if top else by + 0.12 + off
        stacks[corner] = off + qh + 0.18
        _balloon(sheet, (qx, qy, pw, qh), b.kind, top, (bx + bw / 2, by + bh / 2))
        p.drawOn(sheet.c, (qx + BUBBLE_PAD) * inch, (qy + BUBBLE_PAD) * inch)
        sheet.records["text"].append({"page": sheet.page_no, "box": [round(v, 4) for v in (qx, qy, pw, qh)],
                                      "safe": [round(v, 4) for v in safe]})


def _balloon(sheet: Sheet, rect: Box, kind: str, top: bool, toward: tuple[float, float]) -> None:
    c = sheet.c
    x, y, w, h = rect
    c.saveState()
    c.setFillColor(white)
    c.setStrokeColor(black)
    c.setLineWidth(1.2)
    tx = x + w * 0.35 if toward[0] > x + w / 2 else x + w * 0.65
    if kind == "speech":
        base_y = y if top else y + h
        tip_y = base_y - 0.22 if top else base_y + 0.22
        tip_x = tx + (0.12 if toward[0] > tx else -0.12)
        path = c.beginPath()
        path.moveTo((tx - 0.07) * inch, base_y * inch)
        path.lineTo(tip_x * inch, tip_y * inch)
        path.lineTo((tx + 0.07) * inch, base_y * inch)
        path.close()
        c.drawPath(path, stroke=1, fill=1)
    else:  # thought: trail of small circles
        for k, r in enumerate((0.05, 0.035)):
            cy = y - 0.08 - k * 0.1 if top else y + h + 0.08 + k * 0.1
            c.circle(tx * inch, cy * inch, r * inch, stroke=1, fill=1)
    c.roundRect(x * inch, y * inch, w * inch, h * inch, min(h / 2, 0.22) * inch, stroke=1, fill=1)
    if kind == "speech":  # hide the seam between tail and balloon
        c.setStrokeColor(white)
        c.setLineWidth(1.6)
        base_y = y if top else y + h
        c.line((tx - 0.06) * inch, base_y * inch, (tx + 0.06) * inch, base_y * inch)
    c.restoreState()


def _caption(sheet: Sheet, html: str, area: Box, valign: str, safe: Box, offset: float = 0) -> None:
    x, y, w, h = area
    p, ph = sheet.fit_paragraph(html, w - 2 * BUBBLE_PAD, h, sheet.theme.size, min_size=7, align=TA_LEFT,
                                leading=1.2)
    qh = ph + 2 * BUBBLE_PAD
    qy = (y + h - qh - offset) if valign == "top" else y + offset
    c = sheet.c
    c.saveState()
    c.setFillColor(HexColor(CAPTION_FILL))
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(x * inch, qy * inch, w * inch, qh * inch, stroke=1, fill=1)
    c.restoreState()
    p.drawOn(c, (x + BUBBLE_PAD) * inch, (qy + BUBBLE_PAD) * inch)
    sheet.records["text"].append({"page": sheet.page_no, "box": [round(v, 4) for v in (x, qy, w, qh)],
                                  "safe": [round(v, 4) for v in safe]})
