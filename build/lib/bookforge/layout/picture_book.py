"""Picture-book interiors: one illustration per page or spread, typeset text in the safe area."""
from __future__ import annotations

from typing import Callable

from .. import kdp
from ..plan import needs_text_frame, picture_layout, text_space
from ..project import Project
from . import front_matter as fm
from .base import Sheet, frame_box, para_html, text_band
from .geometry import PICTURE_SPOT_ASPECT, SPLIT_IMAGE_FRACTION, fit_box

Draw = Callable[[Sheet, kdp.Interior], None]


def sequence(project: Project) -> list[Draw]:
    """Ordered page drawers, padded to a valid KDP page count."""
    book = project.book
    art = project.art_path
    frame = project.art_path("text-frame") if needs_text_frame(book) else None
    pages: list[Draw] = [
        lambda s, i: fm.title_page(s, i, book, project.art_path("cover-front")),
        lambda s, i: fm.copyright_page(s, i, book),
    ]
    if book.front_matter.dedication:
        pages.append(lambda s, i: fm.dedication_page(s, i, book))

    for n, p in enumerate(book.pages, 1):
        layout = picture_layout(book, n - 1)
        src = art(f"p{n:03d}")
        html = para_html(p.text)
        space = text_space(p, layout)
        if book.lettered(p):  # the words are in the art: the page is the picture
            html = ""
            if layout != "spread":
                pages.append(lambda s, i, src=src: _full_bleed(s, i, src, "", space))
                continue
        elif layout == "text_only" and frame:
            pages.append(lambda s, i, html=html: _framed_text(s, i, frame, html))
            continue
        if layout == "spread":
            if len(pages) % 2 == 0:          # next page would be a recto; spreads start on a verso
                pages.append(lambda s, i: fm.blank_page(s, i, book))
            pages.append(lambda s, i, src=src, html=html, space=space: _spread_half(s, i, src, html, space, 0))
            pages.append(lambda s, i, src=src: _spread_half(s, i, src, "", space, 1))
        else:
            pages.append(lambda s, i, f=_LAYOUTS[layout], src=src, html=html, space=space: f(s, i, src, html, space))

    end_art = project.art_path("the-end") if book.images.text_in_art and book.characters else None
    closing = [lambda s, i: fm.the_end_page(s, i, book, end_art)]
    if book.about_author:
        closing.append(lambda s, i: fm.about_page(s, i, book))
    total = kdp.pad_page_count(len(pages) + len(closing))
    pages += [lambda s, i: fm.blank_page(s, i, book)] * (total - len(pages) - len(closing))
    return pages + closing


def _full_bleed(sheet, interior, src, html, space):
    sheet.image(src, (0, 0, interior.page_w, interior.page_h))
    text_band(sheet, interior, html, space)


def _split(sheet, interior, src, html, space):
    sheet.paper()
    ih = interior.page_h * SPLIT_IMAGE_FRACTION
    sheet.image(src, (0, interior.page_h - ih, interior.page_w, ih))
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    if html:
        sheet.text(html, (x, y, w, interior.page_h - ih - y - 0.25), sheet.theme.size, safe=safe)


def _spot(sheet, interior, src, html, space):
    sheet.paper()
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    box = fit_box((x + w * 0.06, y + h * 0.36, w * 0.88, h * 0.64), PICTURE_SPOT_ASPECT)
    sheet.image(src, box)
    if html:
        sheet.text(html, (x, y, w, box[1] - y - 0.2), sheet.theme.size, safe=safe)


def _text_only(sheet, interior, src, html, space):
    sheet.paper()
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    sheet.text(html, (x + w * 0.08, y, w * 0.84, h), sheet.theme.size * 1.1, safe=safe)


def _framed_text(sheet, interior, frame, html):
    sheet.image(frame, (0, 0, interior.page_w, interior.page_h))
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    fx, fy, fw, fh = frame_box(interior, sheet.page_no)
    sheet.text(html, (fx, fy, fw, fh), sheet.theme.size * 1.1, safe=safe)


def _spread_half(sheet, interior, src, html, space, half):
    fit = (interior.spread_w, interior.page_h)
    crop = (0, interior.page_w / interior.spread_w) if half == 0 else (interior.page_w / interior.spread_w, 1)
    sheet.image(src, (0, 0, interior.page_w, interior.page_h), crop=crop, fit_size=fit)
    text_band(sheet, interior, html, space)


_LAYOUTS = {"full_bleed": _full_bleed, "split": _split, "spot": _spot, "text_only": _text_only}
