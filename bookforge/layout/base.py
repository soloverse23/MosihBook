"""Canvas helpers shared by all book types: fonts, themes, images, auto-fitting text."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from .. import kdp
from ..imaging.fit import prepare
from ..spec import Book
from .geometry import Box

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
_FONT_FILES = {
    "Andika": "Andika-Regular.ttf", "Andika-Bold": "Andika-Bold.ttf",
    "Literata": "Literata.ttf", "Fraunces": "Fraunces.ttf",
    "ComicNeue": "ComicNeue-Regular.ttf", "ComicNeue-Bold": "ComicNeue-Bold.ttf",
    "Bangers": "Bangers-Regular.ttf",
}
for _name, _file in _FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(_name, str(FONTS_DIR / _file)))


@dataclass
class Theme:
    body: str
    body_bold: str
    heading: str
    size: float           # base body size, pt
    align: int
    ink: str = "#2B2622"
    paper: str = "#FFFCF5"
    accent: str = "#C8553D"


THEMES = {
    "picture_book": Theme("Andika", "Andika-Bold", "Fraunces", 21, TA_CENTER),
    "storybook": Theme("Literata", "Literata", "Fraunces", 11.5, TA_JUSTIFY),
    "comic": Theme("ComicNeue-Bold", "ComicNeue-Bold", "Bangers", 9.5, TA_LEFT),
}


def theme_for(book: Book) -> Theme:
    t = THEMES[book.type]
    if book.palette:
        t = Theme(**{**t.__dict__, "accent": book.palette[0]})
    return t


MARK_COLOR = "#7A3DB8"  # violet: the default color of [[marked]] learning words


def marked(text: str, color: str | None = None) -> str:
    """Escape text and turn its [[learning words]] into colored spans."""
    import re
    return re.sub(r"\[\[(.+?)\]\]", lambda m: f'<font color="{color or MARK_COLOR}">{m.group(1)}</font>',
                  escape(text), flags=re.S)


def para_html(text: str, color: str | None = None) -> str:
    """Plain text with blank-line paragraphs and single newlines -> Paragraph markup."""
    return marked(text.strip(), color).replace("\n", "<br/>")


@dataclass
class Sheet:
    """A PDF being drawn page by page; records what preflight needs to verify."""
    path: Path
    page_size: tuple[float, float]
    prepared_dir: Path
    theme: Theme
    page_no: int = 1
    mark_color: str | None = None  # color of [[learning words]] on typeset pages
    records: dict = field(default_factory=lambda: {"images": [], "text": [], "blank": []})

    def __post_init__(self):
        # the initial font must be one of ours: ReportLab's default Helvetica is never embedded
        self.c = canvas.Canvas(str(self.path), pagesize=(self.page_size[0] * inch, self.page_size[1] * inch),
                               initialFontName=self.theme.body)
        self.c.setTitle(self.path.stem)

    def new_page(self) -> None:
        self.c.showPage()
        self.page_no += 1

    def save(self) -> None:
        self.c.save()

    def fill(self, color: str, box: Box | None = None) -> None:
        x, y, w, h = box or (0, 0, *self.page_size)
        self.c.setFillColor(HexColor(color))
        self.c.rect(x * inch, y * inch, w * inch, h * inch, stroke=0, fill=1)

    def paper(self) -> None:
        self.fill(self.theme.paper)

    def blank(self) -> None:
        self.records["blank"].append(self.page_no)

    def image(self, src: Path, box: Box, crop: tuple[float, float] | None = None,
              fit_size: tuple[float, float] | None = None, radius: float = 0) -> None:
        """Draw art into `box`. `fit_size`+`crop` handle a spread cut across two pages;
        `radius` clips the art to a rounded rectangle."""
        x, y, w, h = box
        fw, fh = fit_size or (w, h)
        path, dpi = prepare(src, fw, fh, self.prepared_dir, crop)
        self.c.saveState()
        if radius:
            clip = self.c.beginPath()
            clip.roundRect(x * inch, y * inch, w * inch, h * inch, radius * inch)
            self.c.clipPath(clip, stroke=0, fill=0)
        self.c.drawImage(str(path), x * inch, y * inch, w * inch, h * inch)
        self.c.restoreState()
        self.records["images"].append({"page": self.page_no, "src": src.name, "native_dpi": round(dpi)})

    def style(self, size: float, font: str | None = None, align: int | None = None,
              color: str | None = None, leading: float = 1.38, **extra) -> ParagraphStyle:
        return ParagraphStyle(
            "s", fontName=font or self.theme.body, fontSize=size, leading=size * leading,
            alignment=self.theme.align if align is None else align,
            textColor=HexColor(color or self.theme.ink), spaceAfter=size * 0.6, **extra,
        )

    def fit_paragraph(self, html: str, w: float, max_h: float, size: float, min_size: float = 9,
                      **style_kw) -> tuple[Paragraph, float]:
        """Shrink the font until the text fits; returns (paragraph, height in inches)."""
        while True:
            p = Paragraph(html, self.style(size, **style_kw))
            _, ph = p.wrap(w * inch, max_h * inch)
            if ph <= max_h * inch or size <= min_size:
                if ph > max_h * inch:
                    raise ValueError(f"page {self.page_no}: text does not fit even at {size}pt - shorten it")
                return p, ph / inch
            size -= 0.5

    def text(self, html: str, box: Box, size: float, valign: str = "middle", panel: bool = False,
             safe: Box | None = None, **style_kw) -> Box:
        """Auto-fit text inside `box`; optional rounded paper panel behind it."""
        x, y, w, h = box
        pad = 0.3 if panel else 0
        p, ph = self.fit_paragraph(html, w - 2 * pad, h - 2 * pad, size, **style_kw)
        if panel:  # shrink-wrap the panel around the longest line
            tw = min(w - 2 * pad, max(p.getActualLineWidths0()) / inch + 0.02)
            p.wrap(tw * inch, (h - 2 * pad) * inch)
            x, w = x + (w - tw - 2 * pad) / 2, tw + 2 * pad
        bh = ph + 2 * pad
        by = {"top": y + h - bh, "bottom": y, "middle": y + (h - bh) / 2}[valign]
        if panel:
            c = self.c
            c.saveState()
            c.setFillColor(Color(0, 0, 0, alpha=0.14))  # soft drop shadow
            c.roundRect((x + 0.03) * inch, (by - 0.05) * inch, w * inch, bh * inch, 0.24 * inch, stroke=0, fill=1)
            c.setFillColor(HexColor(self.theme.paper))
            c.setFillAlpha(0.93)
            c.roundRect(x * inch, by * inch, w * inch, bh * inch, 0.24 * inch, stroke=0, fill=1)
            c.restoreState()
        p.drawOn(self.c, (x + pad) * inch, (by + pad) * inch)
        drawn = (x, by, w, bh)
        self.records["text"].append({"page": self.page_no, "box": [round(v, 4) for v in drawn],
                                     "safe": [round(v, 4) for v in (safe or box)]})
        return drawn

    def folio(self, interior: kdp.Interior, on_art: bool = False) -> None:
        """Page number centered on the bottom edge of the safe area (text frames stop above it).
        `on_art`: over a full-page picture, in the bottom outer corner on a small paper disc, clear of the
        words the picture carries."""
        sx, sy, sw, _ = interior.safe_box(self.page_no)
        c = self.c
        if not on_art:
            c.setFont(self.theme.body, 9)
            c.setFillColor(HexColor(self.theme.ink))
            c.drawCentredString((sx + sw / 2) * inch, sy * inch, str(self.page_no))
            return
        r = 0.17
        cx = sx + sw - r if self.page_no % 2 else sx + r  # odd pages are right-hand pages
        cy = sy + r
        c.saveState()
        c.setFillColor(HexColor(self.theme.paper))
        c.setFillAlpha(0.9)
        c.circle(cx * inch, cy * inch, r * inch, stroke=0, fill=1)
        c.restoreState()
        c.setFont(self.theme.body, 9)
        c.setFillColor(HexColor(self.theme.ink))
        c.drawCentredString(cx * inch, (cy - 0.045) * inch, str(self.page_no))
        self.records["text"].append({"page": self.page_no, "box": [round(v, 4) for v in (cx - r, cy - r, 2 * r, 2 * r)],
                                     "safe": [round(v, 4) for v in interior.safe_box(self.page_no)], "folio": True})

def text_band(sheet: Sheet, interior: kdp.Interior, html: str, space: str, size: float | None = None,
              band: float = 0.34, grow_to: float | None = None, min_size: float = 9, width: float = 0.78,
              **style_kw) -> Box | None:
    """Text on a paper panel over full-bleed art, in the band the art prompt kept calm.

    The band starts at `band` of the safe height and grows to `grow_to` at full size; only then
    does the font shrink, down to `min_size`. Raises ValueError if it still does not fit."""
    if not html:
        return None
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    size = size or sheet.theme.size
    grow_to = max(grow_to or band, band)
    steps = [(band + (grow_to - band) * k / 3, size) for k in range(4 if grow_to > band else 1)]
    steps.append((grow_to, min_size))
    valign = space if space in ("top", "bottom") else "middle"
    for k, (frac, floor) in enumerate(steps):
        band_h = h * frac
        by = y + h - band_h if space == "top" else y if space == "bottom" else y + (h - band_h) / 2
        try:
            return sheet.text(html, (x + w * (1 - width) / 2, by, w * width, band_h), size, valign=valign,
                              panel=True, safe=safe, min_size=floor, **style_kw)
        except ValueError:
            if k == len(steps) - 1:
                raise


def frame_box(interior: kdp.Interior, page_no: int) -> Box:
    """The empty centre of the generated `text-frame` art (76% x 80% of the page), within the safe area."""
    x, y, w, h = interior.safe_box(page_no)
    pw, ph = interior.page_w, interior.page_h
    cx, cy, cw, ch = pw * 0.12, ph * 0.10, pw * 0.76, ph * 0.80
    pad = 0.3  # breathing room between the words and the drawn border
    nx, ny = max(x, cx + pad), max(y, cy + pad)
    return nx, ny, min(x + w, cx + cw - pad) - nx, min(y + h, cy + ch - pad) - ny


FOLIO_SPACE = 0.32  # inches reserved at the bottom of the safe area for the page number
