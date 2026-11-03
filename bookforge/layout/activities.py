"""Activity pages drawn by the software for structured (template) books: maze, drawing pages, coloring,
and the maze's answer on the solutions page."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import Flowable

from .. import kdp, maze as mazes
from ..plan import COLORING_HEAD, split_chapter
from ..spec import Book, Page
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


class MazeAnswer(Flowable):
    """A small copy of the book's maze with its path drawn in, for the solutions page."""
    def __init__(self, spec, width_in: float = 2.4):
        super().__init__()
        self.m = mazes.generate(spec.cols, spec.rows, spec.seed)
        self.w_in = width_in
        self.h_in = width_in * self.m.rows / self.m.cols

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, (self.h_in + 0.3) * inch

    def draw(self):
        mazes.draw(self.canv, self.m, (self._aw / inch - self.w_in) / 2 * inch, 0.15 * inch,
                   self.w_in * inch, self.h_in * inch, line=1.2, solution=True)
