"""Words set inside the empty shape a picture left (an oval in a frame, a clearing in a scene).

Each flowable is stacked top-down on the page's axis and given the full width the art leaves free at
its own height, so a page uses the whole calm area instead of the largest rectangle inside it. Nothing
is ever placed where the art has something drawn: if the content does not fit, `place` says so and
draws nothing.
"""
from __future__ import annotations

from reportlab.lib.units import inch

from ..imaging.calm import Shape
from .base import Sheet

PAD = 0.14     # inches kept between a line of words and the edge of the calm area
MIN_W = 2.2    # inches: narrower than this, a block is not worth setting there
COMFORT = 4.6  # inches: a card or picture is happy at this width (if the art allows)
STEP = 0.05    # inches moved down when the shape is too narrow at the current height
CENTRE = 0.42  # share of the leftover height put above the block (a touch above the optical middle)


def _natural(f, cap: float) -> float:
    """The width a block wants: a paragraph's longest line, a card or picture its comfortable measure."""
    if getattr(f, "want", None):
        return min(cap, f.want)
    f.wrap(cap * inch, 1e6)
    lines = getattr(f, "getActualLineWidths0", None)
    if lines:
        return min(cap, max(lines() or [0]) / inch + 0.05)
    return min(cap, COMFORT)


def _stack(flowables, shape: Shape, cx: float, top: float, bottom: float, max_w: float, safe,
           strict: bool = True):
    """strict: each block waits (moves down) for its natural width; otherwise it takes any width >= MIN_W."""
    sx, _, sw, _ = safe
    y, placed = top, []
    for f in flowables:
        cap = getattr(f, "max_w", max_w)  # a block may ask for its own measure (a maze card, a wide table)
        need = max(MIN_W, _natural(f, cap) * 0.97) if strict else MIN_W
        w = cap
        while True:  # where the shape is too narrow (the tip of an oval), move down
            for _ in range(10):
                h = f.wrap(w * inch, 1e6)[1] / inch
                span = shape.span(y, y - h, cx)
                if span is None:
                    avail = 0
                    break
                left, right = max(span[0] + PAD, sx), min(span[1] - PAD, sx + sw)
                avail = min(cap, 2 * min(cx - left, right - cx))  # centred on the page's axis
                if avail >= w - 1e-3 or avail < need:
                    break
                w = avail
            if avail >= w - 1e-3 and avail >= need:
                break
            y -= STEP
            w = cap
            if y - h < bottom:
                return None
        if y - h < bottom:
            return None
        placed.append((f, cx - w / 2, y - h, w, h))
        y -= h + f.getSpaceAfter() / inch
    return placed, top - y


def _axes(shape: Shape, safe) -> list[float]:
    """Vertical axes to centre the words on, best first: the page's middle, then the middle of the
    largest empty area (a frame whose drawing fills one side leaves its calm area off-centre)."""
    from ..imaging.calm import _largest_rect
    sx, _, sw, _ = safe
    c, _, w, _ = _largest_rect(shape.busy)
    rect = (c + w / 2) / shape.cols * shape.pw
    return [sx + sw / 2] + ([rect] if abs(rect - (sx + sw / 2)) > 0.2 else [])


def _layout(flowables, shape: Shape, safe, cx: float, max_w: float):
    """Placements along the axis `cx`, centred vertically in its calm run, or None."""
    from .base import FOLIO_DISC
    sx, sy, sw, sh = safe
    best = None
    for j in range(1, 40):  # the tallest calm run of this column
        bottom, top = shape.extent(cx, shape.ph * j / 40)
        if best is None or top - bottom > best[1] - best[0]:
            best = (bottom, top)
    if best is None or best[1] - best[0] <= 0:
        return None
    top = min(best[1] - PAD, sy + sh)
    bottom = max(best[0] + PAD, sy + FOLIO_DISC)
    for strict in (True, False):
        first = _stack(flowables, shape, cx, top, bottom, max_w, safe, strict)
        if first is None:
            continue
        placed, used = first
        free = (top - bottom) - used
        if free > 0.05:  # centre it vertically, if the narrower rows lower down still take it
            again = _stack(flowables, shape, cx, top - free * CENTRE, bottom, max_w, safe, strict)
            if again is not None:
                placed = again[0]
        return placed
    return None


def place(sheet: Sheet, flowables: list, shape: Shape, safe, max_w: float = 5.4,
          art: str | None = None) -> bool:
    """Set `flowables` centred in the calm area of the page; False (nothing drawn) if they do not fit."""
    placed = None
    for cx in _axes(shape, safe):
        if (placed := _layout(flowables, shape, safe, cx, max_w)) is not None:
            break
    if placed is None:
        return False
    for f, x, y, w, h in placed:
        f.wrap(w * inch, 1e6)  # a failed centring pass may have wrapped it at another width
        f.drawOn(sheet.c, x * inch, y * inch)
        rec = {"page": sheet.page_no, "box": [round(v, 4) for v in (x, y, w, h)], "safe": list(safe)}
        if art:
            rec["art"] = art
        sheet.records["text"].append(rec)
    return True
