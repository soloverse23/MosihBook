"""Title, copyright, dedication and closing pages - shared by every book type."""
from __future__ import annotations

import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch

from .. import kdp
from ..spec import Book
from .base import Sheet, para_html
from .geometry import fit_box


def _ornament(sheet: Sheet, cx: float, y: float) -> None:
    c = sheet.c
    c.setStrokeColor(HexColor(sheet.theme.accent))
    c.setFillColor(HexColor(sheet.theme.accent))
    c.setLineWidth(0.8)
    c.line((cx - 0.9) * inch, y * inch, (cx - 0.12) * inch, y * inch)
    c.line((cx + 0.12) * inch, y * inch, (cx + 0.9) * inch, y * inch)
    c.circle(cx * inch, y * inch, 0.045 * inch, stroke=0, fill=1)


def title_page(sheet: Sheet, interior: kdp.Interior, book: Book, art: Path | None = None) -> None:
    """Cover art as a rounded vignette, then title, ornament, subtitle and author.
    When the cover art carries its own lettered title (text_in_art), it fills the page instead."""
    if art and art.exists() and book.images.text_in_art:
        sheet.image(art, (0, 0, interior.page_w, interior.page_h))
        return
    sheet.paper()
    x, y, w, h = interior.safe_box(sheet.page_no)
    t = sheet.theme
    title_top = y + h * 0.82
    if art and art.exists():
        box = fit_box((x + w * 0.14, y + h * 0.5, w * 0.72, h * 0.5), (interior.trim_w + kdp.BLEED) / interior.page_h)
        sheet.image(art, box, radius=0.18)
        title_top = box[1] - 0.3
    big = min(46, w * 72 / max(8, len(book.title) * 0.5))
    title_box = sheet.text(para_html(book.title), (x, y + h * 0.2, w, title_top - y - h * 0.2), big,
                           valign="top", font=t.heading, align=TA_CENTER, leading=1.1)
    _ornament(sheet, x + w / 2, title_box[1] - 0.25)
    if book.subtitle:
        sheet.text(para_html(book.subtitle), (x, title_box[1] - 1.1, w, 0.7), big * 0.4,
                   valign="top", align=TA_CENTER)
    sheet.text(para_html(book.author.upper()), (x, y, w, 0.5), 12,
               valign="bottom", align=TA_CENTER, font=t.body_bold)


def copyright_page(sheet: Sheet, interior: kdp.Interior, book: Book) -> None:
    sheet.paper()
    x, y, w, h = interior.safe_box(sheet.page_no)
    year = datetime.date.today().year
    lines = book.front_matter.copyright or (
        f"Text copyright © {year} {book.author}\nAll rights reserved.\n\n"
        "No part of this book may be reproduced in any form without written permission "
        "from the author, except for brief quotations in reviews."
    )
    sheet.text(para_html(lines), (x, y, w * 0.85, h * 0.4), 8.5, valign="bottom", align=0)


def dedication_page(sheet: Sheet, interior: kdp.Interior, book: Book) -> None:
    sheet.paper()
    x, y, w, h = interior.safe_box(sheet.page_no)
    sheet.text(para_html(book.front_matter.dedication or ""), (x + w * 0.12, y + h * 0.45, w * 0.76, h * 0.3),
               14, valign="middle", align=TA_CENTER)


def the_end_page(sheet: Sheet, interior: kdp.Interior, book: Book, art: Path | None = None) -> None:
    if art and art.exists():  # "The End" lettered into a closing vignette
        sheet.image(art, (0, 0, interior.page_w, interior.page_h))
        return
    sheet.paper()
    x, y, w, h = interior.safe_box(sheet.page_no)
    box = sheet.text("The End", (x, y + h * 0.42, w, h * 0.2), 40, font=sheet.theme.heading,
                     align=TA_CENTER, valign="middle")
    _ornament(sheet, x + w / 2, box[1] - 0.25)


def about_page(sheet: Sheet, interior: kdp.Interior, book: Book) -> None:
    sheet.paper()
    x, y, w, h = interior.safe_box(sheet.page_no)
    head = sheet.text("About the Author", (x, y + h * 0.62, w, 0.8), 22, font=sheet.theme.heading,
                      align=TA_CENTER, valign="bottom")
    sheet.text(para_html(book.about_author or ""), (x + w * 0.08, y + h * 0.15, w * 0.84, head[1] - y - h * 0.15 - 0.3),
               min(sheet.theme.size, 13), valign="top", align=TA_CENTER)


def blank_page(sheet: Sheet, interior: kdp.Interior, book: Book) -> None:
    sheet.paper()
    sheet.blank()
