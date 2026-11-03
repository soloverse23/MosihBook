"""Layout boxes shared by the art planner and the renderers (inches, origin bottom-left)."""
from __future__ import annotations

Box = tuple[float, float, float, float]  # x, y, w, h

SPLIT_IMAGE_FRACTION = 0.62   # share of page height taken by art in a `split` page
COMIC_GUTTER = 0.14
COMIC_ROWS = {1: [1], 2: [1, 1], 3: [1, 2], 4: [2, 2], 5: [1, 2, 2], 6: [2, 2, 2]}
STORY_SPOT_ASPECT = 4 / 3
PICTURE_SPOT_ASPECT = 5 / 4
# storybook page whose text is too long for a panel on the art: share of page height kept for art
ILLUSTRATED_ART_FRACTIONS = (0.58, 0.48, 0.4)


def panel_boxes(n: int, area: Box) -> list[Box]:
    """Comic grid: rows top-to-bottom, panels left-to-right."""
    x0, y0, w, h = area
    rows = COMIC_ROWS[n]
    row_h = (h - COMIC_GUTTER * (len(rows) - 1)) / len(rows)
    boxes = []
    for r, count in enumerate(rows):
        y = y0 + h - (r + 1) * row_h - r * COMIC_GUTTER
        pw = (w - COMIC_GUTTER * (count - 1)) / count
        for i in range(count):
            boxes.append((x0 + i * (pw + COMIC_GUTTER), y, pw, row_h))
    return boxes


def fit_box(area: Box, aspect: float, anchor: str = "top") -> Box:
    """Largest box with `aspect` inside `area`, centered horizontally."""
    x, y, w, h = area
    bw, bh = w, w / aspect
    if bh > h:
        bw, bh = h * aspect, h
    bx = x + (w - bw) / 2
    by = y + h - bh if anchor == "top" else y + (h - bh) / 2
    return bx, by, bw, bh
