"""Stage 7: check the PDFs against KDP's rules and render proofs + a spread preview."""
from __future__ import annotations

import json
from html import escape

import pypdfium2 as pdfium
from pypdf import PdfReader

from . import kdp
from .project import Project

TOL = 0.5 / 72  # half a point


def _within(box, safe) -> bool:
    x, y, w, h = box
    sx, sy, sw, sh = safe
    return x >= sx - TOL and y >= sy - TOL and x + w <= sx + sw + TOL and y + h <= sy + sh + TOL


def _unembedded_fonts(reader: PdfReader) -> set[str]:
    bad = set()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for f in fonts.values():
            f = f.get_object()
            desc = f.get("/FontDescriptor")
            if f.get("/Subtype") == "/Type0":
                desc = f["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            desc = desc.get_object() if desc else {}
            if not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                bad.add(str(f.get("/BaseFont")))
    return bad


def lettering_problems(project: Project, errors: list, warnings: list) -> None:
    """Words drawn by the image model can't be measured in the PDF; the art review read them instead.
    These are the reviewer's opinion, not KDP rules, so they are warnings: the user may ignore them and
    publish the book as it is."""
    from .art.generate import serious_problems
    from .plan import plan

    slots = [s for s in plan(project.book) if s.lettering]
    if not slots:
        return
    f = project.build / ("review-mock.json" if project.mock else "review.json")
    reviews = json.loads(f.read_text()) if f.exists() else {}
    chosen = reviews.get("_chosen", {})
    for s in slots:
        v = reviews.get(chosen.get(s.id, {}).get("key", ""), {}).get("verdict")
        if v and (problems := serious_problems(v, True)):
            warnings.append(f"{s.id}: " + "; ".join(problems) + " - redo it before uploading")


def lettering_margins(project: Project, errors: list) -> None:
    """Words drawn into a picture must stay inside the 9.7 mm margin. The art review measured each lettered
    picture; one that came too close to an edge is an error until it is redrawn inside the margin
    (imaging.margins), when the review of the new picture decides again."""
    from .imaging import margins
    from .plan import plan

    f = project.build / ("review-mock.json" if project.mock else "review.json")
    reviews = json.loads(f.read_text()) if f.exists() else {}
    chosen = reviews.get("_chosen", {})
    for s in plan(project.book):
        if not s.lettering or not (p := margins.placement(project, s.id)) or not margins.needs_fit(p):
            continue
        v = reviews.get(chosen.get(s.id, {}).get("key", ""), {}).get("verdict")
        if v and not v.get("text_in_safe_area", True):
            errors.append(f"{s.id}: {MARGIN_FIT}")


MARGIN_FIT = "words too close to the page edge (inside the 9.7 mm margin) - redraw it inside the margin"


ON_DRAWING = 0.01  # share of a text box allowed to touch drawn art (anti-aliasing noise)


def text_on_drawing(project: Project, interior: kdp.Interior, texts: list, errors: list) -> None:
    """Words set straight on a picture (no paper panel) must sit on its empty paper: the art under each
    such box is measured again, so no layout can put letters over a character or a drawing unnoticed."""
    from .imaging.calm import busy_fraction
    for t in texts:
        if not t.get("art"):
            continue
        src = project.art / t["art"]
        if src.exists() and busy_fraction(src, interior.page_w, interior.page_h, t["box"]) > ON_DRAWING:
            errors.append(f"page {t['page']}: the text runs over the picture - rebuild the book")


def check(project: Project) -> dict:
    errors, warnings = [], []
    m = json.loads(project.manifest.read_text())
    tw, th = project.book.trim_size
    interior = kdp.Interior(tw, th, m["pages"])
    reader = PdfReader(project.interior_pdf)
    n = len(reader.pages)

    if n != m["pages"]:
        errors.append(f"interior has {n} pages but manifest says {m['pages']}")
    if n < kdp.MIN_PAGES or n > kdp.MAX_PAGES or n % 2:
        errors.append(f"page count {n} must be even and within {kdp.MIN_PAGES}-{kdp.MAX_PAGES}")
    for i, page in enumerate(reader.pages, 1):
        w, h = float(page.mediabox.width) / 72, float(page.mediabox.height) / 72
        if abs(w - interior.page_w) > TOL or abs(h - interior.page_h) > TOL:
            errors.append(f"page {i}: size {w:.3f}x{h:.3f} in, expected {interior.page_w:.3f}x{interior.page_h:.3f}")
    if bad := _unembedded_fonts(reader):
        errors.append(f"fonts not embedded: {sorted(bad)}")
    for t in m["text"]:
        if not _within(t["box"], t["safe"]):
            errors.append(f"page {t['page']}: text box {t['box']} leaves the safe area")
    text_on_drawing(project, interior, m["text"], errors)
    blanks = m["blank"]
    run = 1
    for a, b in zip(blanks, blanks[1:]):
        run = run + 1 if b == a + 1 else 1
        if run > 2 and b != n:  # KDP flags long runs of blank pages inside the book
            warnings.append(f"pages {b - run + 1}-{b} are all blank ({run} in a row): KDP can flag a book with "
                            "long blank stretches - add content to a page there, or ignore this if it is intended")
            break
    lettering_problems(project, errors, warnings)
    lettering_margins(project, errors)
    if m.get("mock_art"):
        warnings.append("this build uses placeholder pictures, not the real art - build again with the real art before uploading")

    cover = None
    if project.cover_pdf.exists():
        cov = kdp.Cover(tw, th, n, project.book.paper)
        info = json.loads((project.build / "cover.json").read_text())
        page = PdfReader(project.cover_pdf).pages[0]
        cw, ch = float(page.mediabox.width) / 72, float(page.mediabox.height) / 72
        if info["pages"] != n:
            errors.append("cover was built for a different page count - rebuild the cover")
        if abs(cw - cov.width) > TOL or abs(ch - cov.height) > TOL:
            errors.append(f"cover is {cw:.3f}x{ch:.3f} in, expected {cov.width:.3f}x{cov.height:.3f}")
        bx, by, bw, bh = cov.barcode_box()
        for t in info["text"]:
            x, y, w, h = t["box"]
            if x < bx + bw and x + w > bx and y < by + bh and y + h > by:
                errors.append("cover text overlaps the barcode area")
            if not _within(t["box"], t["safe"]):
                errors.append(f"cover text box {t['box']} leaves the safe area")
        cover = {"size_in": [round(cov.width, 4), round(cov.height, 4)], "spine_in": round(cov.spine, 4),
                 "spine_text": cov.spine_text_allowed}
    else:
        errors.append("the cover file has not been built yet - build the book again")

    report = {"ok": not errors, "pages": n, "trim": project.book.trim,
              "interior_page_in": [interior.page_w, interior.page_h], "gutter_in": interior.gutter,
              "cover": cover, "errors": errors, "warnings": warnings}
    (project.build / "preflight.json").write_text(json.dumps(report, indent=2))
    return report


def proofs(project: Project, dpi: int = 150) -> None:
    for old in project.proofs.glob("*.png"):
        old.unlink()
    pdf = pdfium.PdfDocument(project.interior_pdf)
    names = []
    for i, page in enumerate(pdf, 1):
        name = f"page-{i:03d}.png"
        page.render(scale=dpi / 72).to_pil().save(project.proofs / name)
        names.append(name)
    if project.cover_pdf.exists():
        pdfium.PdfDocument(project.cover_pdf)[0].render(scale=dpi / 72).to_pil().save(project.proofs / "cover.png")
    _preview_html(project, names)


def _preview_html(project: Project, names: list[str]) -> None:
    """Two-page spreads as a reader sees them: page 1 alone on the right, then 2|3, 4|5..."""
    spreads = [[None, names[0]]] + [names[i:i + 2] for i in range(1, len(names), 2)]
    rows = []
    for s in spreads:
        cells = "".join(
            f'<img src="proofs/{escape(p)}" alt="{escape(p)}">' if p else '<div class="empty"></div>' for p in s
        )
        rows.append(f'<div class="spread">{cells}</div>')
    cover = '<h2>Cover</h2><img class="cover" src="proofs/cover.png" alt="cover">' if project.cover_pdf.exists() else ""
    (project.build / "preview.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(project.book.title)} preview</title>
<style>
:root {{ --bg: #ECE8E1; --ink: #2B2622; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #1E1C1A; --ink: #EEE8E0; }} }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }}
h1, h2 {{ font-weight: 600; text-align: center; }}
.spread {{ display: flex; justify-content: center; margin: 0 auto 28px; max-width: 1100px; }}
.spread img, .empty {{ width: 50%; max-width: 540px; box-shadow: 0 4px 18px rgb(0 0 0 / .18); }}
.empty {{ box-shadow: none; }}
img.cover {{ display: block; margin: 0 auto; width: 100%; max-width: 1100px; box-shadow: 0 4px 18px rgb(0 0 0 / .25); }}
</style></head><body>
<h1>{escape(project.book.title)}</h1>
{cover}
<h2>Interior ({len(names)} pages)</h2>
{''.join(rows)}
</body></html>""")
