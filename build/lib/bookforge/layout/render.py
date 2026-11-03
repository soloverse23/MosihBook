"""Stage 5: render interior.pdf. Re-renders once if the page count moves the KDP gutter."""
from __future__ import annotations

import json

from .. import kdp
from ..project import Project
from . import comic, picture_book, storybook
from .base import Sheet, theme_for


def _render(project: Project, pages_hint: int) -> tuple[int, dict]:
    tw, th = project.book.trim_size
    interior = kdp.Interior(tw, th, pages_hint)
    sheet = Sheet(project.interior_pdf, (interior.page_w, interior.page_h), project.prepared,
                  theme_for(project.book))
    if project.book.type == "storybook":
        storybook.render(sheet, interior, project)
    else:
        seq = (picture_book if project.book.type == "picture_book" else comic).sequence(project)
        for draw in seq:
            draw(sheet, interior)
            sheet.new_page()
    sheet.save()
    return sheet.page_no - 1, sheet.records


def build_interior(project: Project) -> dict:
    missing = sorted({p.name for p in _referenced_art(project)} - {p.name for p in project.art.glob("*.png")})
    if missing:
        raise FileNotFoundError(f"missing art: {', '.join(missing)} - generate all art first (Generate all art in the app, or `bookforge art`)")
    hint = kdp.MIN_PAGES
    for _ in range(3):
        pages, records = _render(project, hint)
        if kdp.gutter(pages) == kdp.gutter(hint):
            break
        hint = pages
    tw, th = project.book.trim_size
    interior = kdp.Interior(tw, th, pages)
    manifest = {
        "pages": pages, "trim": project.book.trim, "page_size_in": [interior.page_w, interior.page_h],
        "gutter_in": interior.gutter, "mock_art": project.mock, **records,
    }
    project.manifest.write_text(json.dumps(manifest, indent=2))
    return manifest


def _referenced_art(project: Project):
    from ..plan import plan
    return [project.art_path(s.id) for s in plan(project.book) if not s.id.startswith(("cover", "char"))]
