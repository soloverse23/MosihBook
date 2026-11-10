"""Reading and sharing copies of a finished book, made from the print PDFs.

The print files carry KDP bleed and padding pages; these copies trim to the page edge, drop the blank
padding and come at screen resolution, so they can be emailed, sold as a download or posted.
Each copy is made on first request and kept in build/exports/ until the print files change.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from .kdp import BLEED

# name -> (download label, what it is for)
KINDS = {
    "reading.pdf": "pages one by one",
    "spreads.pdf": "two-page spreads",
    "pages.zip": "every page as an image",
    "cover.jpg": "front cover image",
}
SCREEN_DPI, IMAGE_DPI, COVER_DPI = 150, 200, 300


def _render(pdf_path: Path, index: int, dpi: int) -> Image.Image:
    doc = pdfium.PdfDocument(pdf_path)
    try:
        return doc[index].render(scale=dpi / 72).to_pil().convert("RGB")
    finally:
        doc.close()


def _crop(im: Image.Image, page_in: tuple[float, float], box_in: tuple[float, float, float, float]) -> Image.Image:
    """Crop a rendered page to a box given in inches from the page's top-left corner."""
    sx, sy = im.width / page_in[0], im.height / page_in[1]
    x, y, w, h = box_in
    return im.crop((round(x * sx), round(y * sy), round((x + w) * sx), round((y + h) * sy)))


def pages(build: Path, dpi: int, keep_blank: bool = False) -> list[Image.Image | None]:
    """Interior pages trimmed to the page edge (bleed off). Blank padding pages are None unless kept."""
    m = json.loads((build / "manifest.json").read_text())
    pw, ph = m["page_size_in"]
    tw, th = pw - BLEED, ph - 2 * BLEED
    blank = set(m.get("blank") or [])
    doc = pdfium.PdfDocument(build / "interior.pdf")
    out = []
    try:
        for i, page in enumerate(doc, 1):
            if i in blank and not keep_blank:
                out.append(None)
                continue
            im = page.render(scale=dpi / 72).to_pil().convert("RGB")
            x = 0.0 if i % 2 else BLEED  # rectos carry bleed on the right, versos on the left
            out.append(_crop(im, (pw, ph), (x, BLEED, tw, th)))
    finally:
        doc.close()
    return out


def cover_panels(build: Path, dpi: int) -> tuple[Image.Image, Image.Image] | None:
    """Front and back of the wraparound cover, trimmed."""
    if not (build / "cover.pdf").exists() or not (build / "cover.json").exists():
        return None
    c = json.loads((build / "cover.json").read_text())
    w, h = c["size_in"]
    tw = (w - c["spine_in"]) / 2 - BLEED
    th = h - 2 * BLEED
    im = _render(build / "cover.pdf", 0, dpi)
    back = _crop(im, (w, h), (BLEED, BLEED, tw, th))
    front = _crop(im, (w, h), (BLEED + tw + c["spine_in"], BLEED, tw, th))
    return front, back


def _pdf(images: list[Image.Image], out: Path, dpi: int) -> None:
    images[0].save(out, "PDF", save_all=True, append_images=images[1:], resolution=dpi, quality=85)


def _spread(left: Image.Image | None, right: Image.Image | None, like: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (like.width * 2, like.height), "white")
    if left:
        canvas.paste(left, (0, 0))
    if right:
        canvas.paste(right, (like.width, 0))
    return canvas


def _make(build: Path, name: str, out: Path) -> None:
    if name == "cover.jpg":
        panels = cover_panels(build, COVER_DPI)
        if not panels:
            raise FileNotFoundError("cover.pdf")
        panels[0].save(out, "JPEG", quality=92, dpi=(COVER_DPI, COVER_DPI))
        return
    dpi = IMAGE_DPI if name == "pages.zip" else SCREEN_DPI
    inner = pages(build, dpi)
    cover = cover_panels(build, dpi)
    front, back = cover if cover else (None, None)
    if name == "reading.pdf":
        _pdf([p for p in (front, *inner, back) if p], out, dpi)
    elif name == "spreads.pdf":
        # as the open book reads: cover alone, page 1 alone on the right, then 2|3, 4|5 ... back alone
        like = next(p for p in inner if p)
        sheets = [front] if front else []
        sheets.append(_spread(None, inner[0], like))
        for i in range(1, len(inner), 2):
            left, right = inner[i], inner[i + 1] if i + 1 < len(inner) else None
            if left or right:
                sheets.append(_spread(left, right, like))
        if back:
            sheets.append(back)
        _pdf(sheets, out, dpi)
    elif name == "pages.zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:  # JPEGs don't compress further
            def put(fname, im):
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=90, dpi=(dpi, dpi))
                z.writestr(fname, buf.getvalue())
            if front:
                put("00-cover-front.jpg", front)
            n = 0
            for p in inner:
                if p:
                    n += 1
                    put(f"page-{n:02d}.jpg", p)
            if back:
                put(f"{n + 1:02d}-cover-back.jpg", back)
    else:
        raise KeyError(name)


def get(build: Path, name: str) -> Path:
    """The export `name`, made now if missing or older than the print files."""
    if name not in KINDS:
        raise KeyError(name)
    if not (build / "interior.pdf").exists():
        raise FileNotFoundError("interior.pdf")
    out = build / "exports" / name
    sources = [build / n for n in ("interior.pdf", "cover.pdf") if (build / n).exists()]
    if not out.exists() or out.stat().st_mtime < max(s.stat().st_mtime for s in sources):
        out.parent.mkdir(exist_ok=True)
        tmp = out.with_name(f".{name}.part")
        _make(build, name, tmp)
        tmp.replace(out)
    return out


def ready(build: Path) -> dict[str, int]:
    """Sizes of the exports already made and still current."""
    sources = [build / n for n in ("interior.pdf", "cover.pdf") if (build / n).exists()]
    if not sources:
        return {}
    newest = max(s.stat().st_mtime for s in sources)
    return {n: f.stat().st_size for n in KINDS
            if (f := build / "exports" / n).exists() and f.stat().st_mtime >= newest}
