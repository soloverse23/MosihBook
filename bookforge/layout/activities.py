"""Activity pages drawn by the software for structured (template) books: maze, drawing pages, coloring,
matching, fill-in, odd one out, the final challenge's certificate, and every answer on the solutions page."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph

from .. import kdp, maze as mazes
from ..plan import COLORING_HEAD, split_chapter
from ..spec import Book, CertificateSpec, Page
from ..words import word
from .base import Sheet, para_html

HEAD = 1.15  # inches at the top of an activity page for its title and instruction


def _color(book: Book) -> str | None:
    return book.learning.color if book.learning else None


def heading(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, height: float = HEAD) -> float:
    """Title (the page's chapter) and instruction at the top of the safe area. Returns the y below them."""
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    top = y + h
    title = split_chapter(p.chapter)[1] if p.chapter else ""
    html = (f'<font name="{sheet.theme.heading}" size="20">{para_html(title)}</font><br/>' if title else "") \
        + para_html(p.text, _color(book))
    if html:
        sheet.text(html, (x, top - height, w, height), 13, valign="top", safe=safe, min_size=9,
                   align=TA_CENTER, autoLeading="max")
    return top - height


def _rounded_frame(sheet: Sheet, box) -> None:
    x, y, w, h = box
    c = sheet.c
    c.saveState()
    c.setStrokeColor(HexColor(sheet.theme.accent))
    c.setLineWidth(2)
    c.setDash(7, 5)
    c.roundRect(x * inch, y * inch, w * inch, h * inch, 0.25 * inch, stroke=1, fill=0)
    c.restoreState()


def drawing_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page) -> None:
    """Guided drawing / imagination: the instruction, then a big empty frame to draw in."""
    sheet.paper()
    below = heading(sheet, interior, book, p, height=1.6)
    x, y, w, _ = interior.safe_box(sheet.page_no)
    _rounded_frame(sheet, (x, y + 0.35, w, below - y - 0.55))


def coloring_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, art: Path) -> None:
    """White page: the instruction on top, the line art below it."""
    sheet.fill("#FFFFFF")
    below = heading(sheet, interior, book, p, height=COLORING_HEAD)
    x, y, w, _ = interior.safe_box(sheet.page_no)
    if art.exists():
        sheet.image(art, (x, y, w, below - y))


def maze_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, start: Path, goal: Path) -> None:
    sheet.paper()
    below = heading(sheet, interior, book, p)
    x, y, w, _ = interior.safe_box(sheet.page_no)
    end = min(1.3, w * 0.22)  # the start and goal vignettes
    m = mazes.generate(p.maze.cols, p.maze.rows, p.maze.seed)
    box = (x, y + end, w, below - y - 2 * end)
    cell, _ = mazes.draw(sheet.c, m, *(v * inch for v in box), line=3.2)
    cell /= inch
    left = x + (w - cell * m.cols) / 2
    top = box[1] + (box[3] + cell * m.rows) / 2
    bottom = top - cell * m.rows
    if start.exists():  # above the entrance (top-left cell), the goal below the exit (bottom-right)
        sheet.image(start, (max(x, left + cell / 2 - end / 2), top + 0.02, end, end))
    if goal.exists():
        sheet.image(goal, (min(x + w - end, left + cell * (m.cols - 0.5) - end / 2), bottom - end - 0.02, end, end))


class Block(Flowable):
    """Flowables kept on one page: a game's title with its answer. Never split, so a frame that is too full
    moves the whole block to the next page (ReportLab's KeepTogether needs a page template to do that)."""
    def __init__(self, parts):
        super().__init__()
        self.parts = parts

    def wrap(self, aw, ah):
        self._sizes = [f.wrap(aw, ah) for f in self.parts]
        self.width = aw
        self.height = sum(h + f.getSpaceAfter() for f, (_, h) in zip(self.parts, self._sizes))
        return aw, self.height

    def split(self, aw, ah):
        return []

    def draw(self):
        y = self.height
        for f, (_, h) in zip(self.parts, self._sizes):
            y -= h
            f.drawOn(self.canv, 0, y)
            y -= f.getSpaceAfter()


class MazeAnswer(Flowable):
    """A small copy of the book's maze with its path drawn in, for the solutions page."""
    def __init__(self, spec, width_in: float = 2.4):
        super().__init__()
        self.m = mazes.generate(spec.cols, spec.rows, spec.seed)
        self.w_in = width_in
        self.h_in = width_in * self.m.rows / self.m.cols

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, (self.h_in + 0.15) * inch

    def draw(self):
        mazes.draw(self.canv, self.m, (self._aw / inch - self.w_in) / 2 * inch, 0.05 * inch,
                   self.w_in * inch, self.h_in * inch, line=1.2, solution=True)


# ---------- games laid out from their data (matching, fill-in, odd one out, final challenge) ----------
VIGNETTE = 1.25   # inches: the optional small picture centered under a game
FOLIO_ROOM = 0.42  # the page number's disc sits in the bottom outer corner


def _body(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, art: Path | None) -> tuple:
    """Paper, title and instruction, the optional vignette at the bottom; returns the box left for the game."""
    sheet.paper()
    below = heading(sheet, interior, book, p)
    x, y, w, _ = interior.safe_box(sheet.page_no)
    bottom = y + FOLIO_ROOM
    if art is not None and art.exists():
        sheet.image(art, (x + (w - VIGNETTE) / 2, y, VIGNETTE, VIGNETTE))
        bottom = y + VIGNETTE + 0.1
    return x, bottom, w, below - bottom - 0.15


def _dot(sheet: Sheet, cx: float, cy: float, r: float = 0.07) -> None:
    c = sheet.c
    c.saveState()
    c.setFillColor(HexColor(sheet.theme.accent))
    c.circle(cx * inch, cy * inch, r * inch, stroke=0, fill=1)
    c.restoreState()


def derangement(n: int, seed: int) -> list[int]:
    """A shuffled order where no item stays on its own row (so no pair reads straight across)."""
    import random
    order = list(range(n))
    rnd = random.Random(seed)
    for _ in range(200):
        rnd.shuffle(order)
        if all(o != i for i, o in enumerate(order)):
            return order
    return order[1:] + order[:1]


def matching_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, n: int, art: Path | None) -> None:
    """Two columns with a dot beside each item; the child draws a line from each left item to its partner."""
    x, y, w, h = _body(sheet, interior, book, p, art)
    pairs = p.matching.pairs
    k = len(pairs)
    right = derangement(k, n)
    row = min(h / k, 1.0)
    top = y + (h + row * k) / 2
    col = w * 0.36
    safe = interior.safe_box(sheet.page_no)
    color = _color(book)
    for i in range(k):
        cy = top - (i + 0.5) * row
        box_y, box_h = cy - row / 2 + 0.04, row - 0.08
        sheet.text(para_html(pairs[i][0], color), (x, box_y, col, box_h), 16, safe=safe, min_size=8,
                   align=TA_RIGHT)
        sheet.text(para_html(pairs[right[i]][1], color), (x + w - col, box_y, col, box_h), 16, safe=safe,
                   min_size=8, align=TA_LEFT)
        _dot(sheet, x + col + 0.16, cy)
        _dot(sheet, x + w - col - 0.16, cy)


def _blank(html: str, accent: str) -> str:
    import re
    return re.sub(r"_{3,}", f'<font color="{accent}">____________</font>', html)


def fill_in_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, art: Path | None) -> None:
    """Numbered items; '___' becomes a blank to write in, an item without one gets a writing line under it."""
    x, y, w, h = _body(sheet, interior, book, p, art)
    items = p.fill_in.items
    band = min(h / len(items), 1.15)
    top = y + h
    safe = interior.safe_box(sheet.page_no)
    c = sheet.c
    for i, it in enumerate(items):
        by = top - (i + 1) * band
        has_blank = "___" in it.prompt
        html = f"<b>{i + 1}.</b> " + _blank(para_html(it.prompt, _color(book)), sheet.theme.accent)
        text_h = band - 0.1 if has_blank else band * 0.6
        sheet.text(html, (x, by + band - text_h, w, text_h), 15, valign="middle" if has_blank else "top",
                   safe=safe, min_size=8, align=TA_LEFT)
        if not has_blank:
            c.saveState()
            c.setStrokeColor(HexColor(sheet.theme.accent))
            c.setLineWidth(1)
            c.setDash(2, 3)
            c.line((x + 0.3) * inch, (by + 0.14) * inch, (x + w) * inch, (by + 0.14) * inch)
            c.restoreState()


def odd_one_out_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page, art: Path | None) -> None:
    """One row of rounded tiles per group; the child circles the tile that does not belong."""
    x, y, w, h = _body(sheet, interior, book, p, art)
    groups = p.odd_one_out.groups
    band = min(h / len(groups), 1.2)
    top = y + (h + band * len(groups)) / 2
    safe = interior.safe_box(sheet.page_no)
    c = sheet.c
    num_w, gap = 0.4, 0.14
    for gi, g in enumerate(groups):
        cy = top - (gi + 0.5) * band
        tile_h = min(band * 0.62, 0.62)
        sheet.text(f'<font name="{sheet.theme.heading}" color="{sheet.theme.accent}">{gi + 1}</font>',
                   (x, cy - tile_h / 2, num_w, tile_h), 18, safe=safe, min_size=10, align=TA_CENTER)
        m = len(g.items)
        tw = (w - num_w - gap * (m - 1)) / m
        for j, item in enumerate(g.items):
            tx = x + num_w + j * (tw + gap)
            c.saveState()
            c.setFillColor(HexColor("#FFFFFF"))
            c.setStrokeColor(HexColor(sheet.theme.ink))
            c.setLineWidth(1.2)
            c.roundRect(tx * inch, (cy - tile_h / 2) * inch, tw * inch, tile_h * inch, 0.12 * inch, stroke=1, fill=1)
            c.restoreState()
            sheet.text(para_html(item, _color(book)), (tx + 0.06, cy - tile_h / 2 + 0.04, tw - 0.12, tile_h - 0.08),
                       15, safe=safe, min_size=7, align=TA_CENTER)


def _star(sheet: Sheet, cx: float, cy: float, r: float) -> None:
    import math
    c = sheet.c
    path = c.beginPath()
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        px, py = (cx + rr * math.cos(a)) * inch, (cy + rr * math.sin(a)) * inch
        path.moveTo(px, py) if i == 0 else path.lineTo(px, py)
    path.close()
    c.saveState()
    c.setFillColor(HexColor(sheet.theme.accent))
    c.drawPath(path, stroke=0, fill=1)
    c.restoreState()


def final_challenge_page(sheet: Sheet, interior: kdp.Interior, book: Book, p: Page) -> None:
    """The last challenge on top, a small certificate with lines for the child's name and the date below."""
    sheet.paper()
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    cert_h = min(3.3, h * 0.46)
    cy0 = y + FOLIO_ROOM
    heading(sheet, interior, book, p, height=h - cert_h - FOLIO_ROOM - 0.25)
    cw = min(w, 5.6)
    cx0 = x + (w - cw) / 2
    c = sheet.c
    c.saveState()
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(HexColor(sheet.theme.accent))
    c.setLineWidth(3)
    c.roundRect(cx0 * inch, cy0 * inch, cw * inch, cert_h * inch, 0.2 * inch, stroke=1, fill=1)
    c.setLineWidth(1)
    c.roundRect((cx0 + 0.12) * inch, (cy0 + 0.12) * inch, (cw - 0.24) * inch, (cert_h - 0.24) * inch,
                0.14 * inch, stroke=1, fill=0)
    c.restoreState()
    cert = p.certificate or CertificateSpec()
    title = cert.title or word(book, "well_done")
    labels = (cert.name_label or word(book, "name"), cert.date_label or word(book, "date"))
    _star(sheet, cx0 + cw / 2, cy0 + cert_h - 0.5, 0.26)
    sheet.text(f'<font name="{sheet.theme.heading}">{para_html(title)}</font>',
               (cx0 + 0.3, cy0 + cert_h - 1.3, cw - 0.6, 0.5), 22, safe=safe, min_size=12, align=TA_CENTER)
    for k, label in enumerate(labels):
        ly = cy0 + 0.45 + (1 - k) * 0.7
        c.setFont(sheet.theme.body, 13)
        c.setFillColor(HexColor(sheet.theme.ink))
        c.drawString((cx0 + 0.4) * inch, (ly + 0.1) * inch, label)
        lx = cx0 + 0.4 + stringWidth(label, sheet.theme.body, 13) / inch + 0.12
        c.saveState()
        c.setStrokeColor(HexColor(sheet.theme.ink))
        c.setLineWidth(0.8)
        c.line(lx * inch, (ly + 0.04) * inch, (cx0 + cw - 0.4) * inch, (ly + 0.04) * inch)
        c.restoreState()


class Card(Block):
    """A Block on a soft rounded white card: one game's answers on the solutions page."""
    PAD = 7  # points

    def __init__(self, parts, gap: float = 8):
        super().__init__(parts)
        self.gap = gap

    def wrap(self, aw, ah):
        _, h = super().wrap(aw - 2 * self.PAD, ah)
        self.width, self.height = aw, h + 2 * self.PAD
        return aw, self.height

    def getSpaceAfter(self):
        return self.gap

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFillAlpha(0.72)
        c.setStrokeColor(HexColor(self._accent))
        c.setStrokeAlpha(0.35)
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.width, self.height, 9, stroke=1, fill=1)
        c.restoreState()
        c.saveState()
        c.translate(self.PAD, self.PAD)
        y = self.height - 2 * self.PAD
        for f, (_, h) in zip(self.parts, self._sizes):
            y -= h
            f.drawOn(c, 0, y)
            y -= f.getSpaceAfter()
        c.restoreState()


def answers(sheet: Sheet, book: Book, scale: float = 1.0) -> list:
    """The solutions page's answers, made from the games' own data in page order (so they always match):
    one card per game, its name on top in the accent color and the answers centred below. `scale` shrinks
    it all so the page fits on one page."""
    accent = sheet.theme.accent
    label = sheet.style(12.5 * scale, font=sheet.theme.heading, align=TA_CENTER, color=accent, leading=1.2)
    label.spaceAfter = 1
    body = sheet.style(11 * scale, align=TA_CENTER, leading=1.45)
    body.spaceAfter = 0
    out = []
    for n, p in enumerate(book.pages, 1):
        name = (split_chapter(p.chapter)[1] if p.chapter else "") or f"p. {n}"
        if p.kind == "maze" and p.maze:
            parts = [Paragraph(para_html(name), label), MazeAnswer(p.maze, min(1.5, 1.25 * p.maze.cols / p.maze.rows) * scale)]
        elif not p.drawn_activity or p.kind == "final_challenge":
            continue
        else:
            if p.matching:
                lines = [f"{para_html(a)}&nbsp;—&nbsp;{para_html(b)}" for a, b in p.matching.pairs]  # a pair never breaks
            elif p.fill_in:
                lines = [f'<font color="{accent}">{i}.</font>&nbsp;{para_html(it.answer)}'
                         for i, it in enumerate(p.fill_in.items, 1)]
            else:
                lines = [f'<font color="{accent}">{i}.</font>&nbsp;{para_html(g.answer)}'
                         for i, g in enumerate(p.odd_one_out.groups, 1)]
            parts = [Paragraph(para_html(name), label), Paragraph("&nbsp;&nbsp;&nbsp; ".join(lines), body)]
        card = Card(parts, gap=8 * scale)
        card._accent = accent
        if p.kind == "maze":
            card.max_w = max(2.6, 1.5 * scale + 1.0)  # the maze with a little air, not a wide empty card
        out.append(card)
    return out
