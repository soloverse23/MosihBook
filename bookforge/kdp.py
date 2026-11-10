"""Amazon KDP paperback geometry. Every print measurement lives here, in inches.

Source: KDP Help, "Set trim size, bleed, and margins" and "Create a paperback cover".
"""
from __future__ import annotations

from dataclasses import dataclass

BLEED = 0.125
SAFE = 0.375          # min margin from trim on outside/top/bottom for bleed books
MIN_PAGES = 24
MAX_PAGES = 828
SPINE_TEXT_MIN_PAGES = 80   # KDP: spine text only for books with more than 79 pages
SPINE_TEXT_MARGIN = 0.0625  # keep spine text this far from each fold
BARCODE_W, BARCODE_H = 2.0, 1.2
BARCODE_INSET = 0.25        # barcode box sits this far from back-cover trim (bottom/right)
MIN_DPI = 300

# inches of spine per page
SPINE_FACTOR = {
    "white_bw": 0.002252,
    "cream_bw": 0.0025,
    "standard_color": 0.002252,
    "premium_color": 0.002347,
}

# (max page count, gutter/inside margin)
GUTTER_STEPS = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]

TRIMS = {"5x8", "5.5x8.5", "6x9", "6.14x9.21", "7x10", "8x10", "8.25x8.25", "8.5x8.5", "8.5x11", "8.25x11", "8.27x11.69"}


def parse_trim(trim: str) -> tuple[float, float]:
    w, h = trim.lower().split("x")
    return float(w), float(h)


def gutter(pages: int) -> float:
    for limit, g in GUTTER_STEPS:
        if pages <= limit:
            return g
    raise ValueError(f"{pages} pages exceeds KDP maximum of {MAX_PAGES}")


def spine_width(pages: int, paper: str) -> float:
    return pages * SPINE_FACTOR[paper]


def pad_page_count(pages: int) -> int:
    """KDP needs at least 24 pages and an even count."""
    pages = max(pages, MIN_PAGES)
    return pages + (pages % 2)


@dataclass(frozen=True)
class Interior:
    trim_w: float
    trim_h: float
    pages: int

    @property
    def page_w(self) -> float:  # bleed on the outside edge only
        return self.trim_w + BLEED

    @property
    def page_h(self) -> float:
        return self.trim_h + 2 * BLEED

    @property
    def gutter(self) -> float:
        return gutter(self.pages)

    @staticmethod
    def is_recto(page_no: int) -> bool:
        """Page 1 is a right-hand page; odd pages are rectos."""
        return page_no % 2 == 1

    def trim_x(self, page_no: int) -> float:
        """x of the trim box's left edge on the page (verso pages carry bleed on the left)."""
        return 0.0 if self.is_recto(page_no) else BLEED

    def safe_box(self, page_no: int) -> tuple[float, float, float, float]:
        """(x, y, w, h) of the live area, measured from the page's bottom-left corner."""
        tx = self.trim_x(page_no)
        left = self.gutter if self.is_recto(page_no) else SAFE
        right = SAFE if self.is_recto(page_no) else self.gutter
        x = tx + left
        y = BLEED + SAFE
        return x, y, self.trim_w - left - right, self.trim_h - 2 * SAFE

    @property
    def spread_w(self) -> float:
        return 2 * self.trim_w + 2 * BLEED


@dataclass(frozen=True)
class Cover:
    trim_w: float
    trim_h: float
    pages: int
    paper: str

    @property
    def spine(self) -> float:
        return spine_width(self.pages, self.paper)

    @property
    def width(self) -> float:
        return BLEED + self.trim_w + self.spine + self.trim_w + BLEED

    @property
    def height(self) -> float:
        return self.trim_h + 2 * BLEED

    @property
    def spine_x(self) -> float:
        return BLEED + self.trim_w

    @property
    def front_x(self) -> float:
        return self.spine_x + self.spine

    @property
    def spine_text_allowed(self) -> bool:
        return self.pages >= SPINE_TEXT_MIN_PAGES

    def barcode_box(self) -> tuple[float, float, float, float]:
        x = self.spine_x - BARCODE_INSET - BARCODE_W
        y = BLEED + BARCODE_INSET
        return x, y, BARCODE_W, BARCODE_H
