"""Reading and sharing copies made from the print PDFs: trimmed, no padding pages, the cover around them."""
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from bookforge import exports
from bookforge.art import generate
from bookforge.layout.cover import build_cover
from bookforge.layout.render import build_interior
from bookforge.project import Project

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "picture-book" / "book.yaml"


def test_exports(tmp_path):
    shutil.copy(EXAMPLE, tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p, log=lambda m: None)
    m = build_interior(p)
    build_cover(p)
    pages = m["pages"] - len(m.get("blank") or [])
    trim_w, trim_h = (float(x) for x in m["trim"].split("x"))

    reading = PdfReader(exports.get(p.build, "reading.pdf"))
    assert len(reading.pages) == pages + 2  # front cover, the pages, back cover
    box = reading.pages[1].mediabox
    assert abs(float(box.width) / 72 - trim_w) < 0.02 and abs(float(box.height) / 72 - trim_h) < 0.02  # bleed off

    spreads = PdfReader(exports.get(p.build, "spreads.pdf"))
    assert abs(float(spreads.pages[2].mediabox.width) / 72 - 2 * trim_w) < 0.03

    with zipfile.ZipFile(exports.get(p.build, "pages.zip")) as z:
        assert len(z.namelist()) == pages + 2 and z.namelist()[0] == "00-cover-front.jpg"

    with Image.open(exports.get(p.build, "cover.jpg")) as im:
        assert abs(im.width / im.height - trim_w / trim_h) < 0.01

    assert set(exports.ready(p.build)) == set(exports.KINDS)
    p.interior_pdf.touch()  # a new build makes them stale
    assert exports.ready(p.build) == {}
    assert json.loads((p.build / "manifest.json").read_text())["pages"] == m["pages"]
