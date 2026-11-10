"""Where words can go on a picture: the largest plain, empty rectangle the art really left.

Generated art does not always keep the space its prompt asked for (a frame whose characters reach into
the middle, a scene with a leaf across the calm band), so text is never placed on a guessed box: the
picture itself is measured. A cell is calm when its color is close to the art's paper color and it has
no detail; busy cells are grown by a margin so letters keep their distance from the drawing.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat

GRID = 120          # cells across the page
TOLERANCE = 22      # max per-channel distance from the paper color (0-255)
MARGIN = 2          # cells of clearance kept around anything drawn


def _fit(im: Image.Image, aspect: float) -> Image.Image:
    """The same centered cover-crop the page applies when it prints the art (imaging.fit)."""
    if im.width / im.height > aspect:
        nw = round(im.height * aspect)
        x = (im.width - nw) // 2
        return im.crop((x, 0, x + nw, im.height))
    nh = round(im.width / aspect)
    y = (im.height - nh) // 2
    return im.crop((0, y, im.width, y + nh))


def busy_mask(src: Path, aspect: float) -> tuple[list[list[bool]], int, int]:
    """Grid of booleans (row 0 = top of the page): True where the art has something drawn."""
    with Image.open(src) as im:
        im = _fit(ImageOps.exif_transpose(im).convert("RGB"), aspect)
    cols = GRID
    rows = max(1, round(GRID / aspect))
    small = im.resize((cols * 3, rows * 3), Image.BILINEAR)
    # paper color: the median of the page's centre, where a frame keeps its plain paper
    cw, ch = small.width, small.height
    centre = small.crop((int(cw * 0.35), int(ch * 0.4), int(cw * 0.65), int(ch * 0.6)))
    paper = [int(v) for v in ImageStat.Stat(centre).median]
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES)
    sp, ep = small.load(), edges.load()
    raw = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            for dy in range(3):
                for dx in range(3):
                    x, y = c * 3 + dx, r * 3 + dy
                    p = sp[x, y]
                    if max(abs(p[0] - paper[0]), abs(p[1] - paper[1]), abs(p[2] - paper[2])) > TOLERANCE \
                            or ep[x, y] > 28:
                        raw[r][c] = True
                        break
                if raw[r][c]:
                    break
    busy = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if raw[r][c]:
                for rr in range(max(0, r - MARGIN), min(rows, r + MARGIN + 1)):
                    for cc in range(max(0, c - MARGIN), min(cols, c + MARGIN + 1)):
                        busy[rr][cc] = True
    return busy, cols, rows


def _largest_rect(busy: list[list[bool]]) -> tuple[int, int, int, int]:
    """(col, row, width, height) in cells of the largest all-calm rectangle (row = top row)."""
    rows, cols = len(busy), len(busy[0])
    heights = [0] * cols
    best = (0, 0, 0, 0)
    best_area = 0
    for r in range(rows):
        for c in range(cols):
            heights[c] = 0 if busy[r][c] else heights[c] + 1
        stack: list[int] = []
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            while stack and heights[stack[-1]] >= h:
                top = stack.pop()
                height = heights[top]
                left = stack[-1] + 1 if stack else 0
                width = c - left
                if height * width > best_area:
                    best_area = height * width
                    best = (left, r - height + 1, width, height)
            stack.append(c)
    return best


@lru_cache(maxsize=64)
def _calm_fractions(src: str, mtime: int, aspect: float) -> tuple[float, float, float, float]:
    busy, cols, rows = _mask_cached(src, mtime, aspect)
    c, r, w, h = _largest_rect(busy)
    # fractions of the page, origin bottom-left like the PDF
    return c / cols, 1 - (r + h) / rows, w / cols, h / rows


def calm_box(src: Path, page_w: float, page_h: float) -> tuple[float, float, float, float]:
    """The largest empty rectangle of art printed full-page at page_w x page_h inches, in inches
    from the page's bottom-left corner. (0, 0, 0, 0) when the art has no plain area at all."""
    fx, fy, fw, fh = _calm_fractions(str(src), src.stat().st_mtime_ns, round(page_w / page_h, 5))
    return fx * page_w, fy * page_h, fw * page_w, fh * page_h


def busy_fraction(src: Path, page_w: float, page_h: float, box) -> float:
    """Share of the cells under `box` (inches, bottom-left origin) where the art has something drawn."""
    busy, cols, rows = _mask_cached(str(src), src.stat().st_mtime_ns, round(page_w / page_h, 5))
    x, y, w, h = box
    c0, c1 = int(x / page_w * cols), int((x + w) / page_w * cols + 0.999)
    r0, r1 = int((1 - (y + h) / page_h) * rows), int((1 - y / page_h) * rows + 0.999)
    cells = [busy[r][c] for r in range(max(0, r0), min(rows, r1)) for c in range(max(0, c0), min(cols, c1))]
    return sum(cells) / len(cells) if cells else 0.0


@lru_cache(maxsize=64)
def _mask_cached(src: str, mtime: int, aspect: float):
    return busy_mask(Path(src), aspect)


class Shape:
    """The empty area of a full-page picture, cell by cell: where words can go at each height.
    Inches from the page's bottom-left corner, like the PDF."""

    def __init__(self, busy: list[list[bool]], page_w: float, page_h: float):
        self.busy, self.pw, self.ph = busy, page_w, page_h
        self.rows, self.cols = len(busy), len(busy[0])

    def _rows(self, top: float, bottom: float) -> range:
        r0 = int((1 - top / self.ph) * self.rows)
        r1 = int((1 - bottom / self.ph) * self.rows + 0.999)
        return range(max(0, r0), min(self.rows, r1))

    def _col(self, x: float) -> int:
        return min(self.cols - 1, max(0, int(x / self.pw * self.cols)))

    def span(self, top: float, bottom: float, cx: float) -> tuple[float, float] | None:
        """The calm horizontal run through `cx` that stays calm on every row from `bottom` to `top`."""
        rows = self._rows(top, bottom)
        if not rows or bottom < 0 or top > self.ph:
            return None
        calm = lambda c: not any(self.busy[r][c] for r in rows)
        c = self._col(cx)
        if not calm(c):
            return None
        left = right = c
        while left > 0 and calm(left - 1):
            left -= 1
        while right < self.cols - 1 and calm(right + 1):
            right += 1
        return left / self.cols * self.pw, (right + 1) / self.cols * self.pw

    def extent(self, cx: float, y: float) -> tuple[float, float]:
        """(bottom, top) of the calm run of column `cx` through height `y`."""
        c, r = self._col(cx), min(self.rows - 1, max(0, int((1 - y / self.ph) * self.rows)))
        if self.busy[r][c]:
            return y, y
        top = bot = r
        while top > 0 and not self.busy[top - 1][c]:
            top -= 1
        while bot < self.rows - 1 and not self.busy[bot + 1][c]:
            bot += 1
        return (1 - (bot + 1) / self.rows) * self.ph, (1 - top / self.rows) * self.ph


def shape_of(src: Path, page_w: float, page_h: float) -> Shape:
    busy, _, _ = _mask_cached(str(src), src.stat().st_mtime_ns, round(page_w / page_h, 5))
    return Shape(busy, page_w, page_h)


def rect_shape(box, page_w: float, page_h: float) -> Shape:
    """A Shape that is calm only inside `box`: plain paper pages use the same placement as art pages."""
    x, y, w, h = box
    cols, rows = GRID, max(1, round(GRID * page_h / page_w))
    busy = [[not (x <= (c + 0.5) / cols * page_w <= x + w and y <= (1 - (r + 0.5) / rows) * page_h <= y + h)
             for c in range(cols)] for r in range(rows)]
    return Shape(busy, page_w, page_h)


if __name__ == "__main__":  # python -m bookforge.imaging.calm art.png 8.5 11
    import sys
    print(json.dumps([round(v, 3) for v in calm_box(Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]))]))
