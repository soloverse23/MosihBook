"""A book that follows a template structure: learning marks, activity pages, exact page count."""
import asyncio

import pytest
import yaml

from bookforge import author, spec, templates
from bookforge.art import generate
from bookforge.layout.base import marked
from bookforge.layout.cover import build_cover
from bookforge.layout.render import build_interior
from bookforge.plan import plan
from bookforge.preflight import check
from bookforge.project import Project

MARKING = "the adjective in violet, its opposite in parentheses right after it"


def structured_book(text_in_art: bool) -> dict:
    t = templates.get("anahita-40")
    secs = [s.model_dump(exclude_none=True) for s in t.active()]
    pages = []
    for s in t.active():
        for k in range(s.pages):
            pg = {"kind": s.kind, "text": f"{s.kind} {k + 1}"}
            if k == 0:
                pg["chapter"] = s.title or s.kind
            if s.kind == "story":
                pg.update(text="La mer est [[chaude (froide)]].\nNina est [[petite (grande)]].",
                          prompt="Nina on a sunny beach", illustration="opener")
            elif s.kind in ("coloring", "observation", "parents_note", "comprehension", "theme_intro",
                            "reference", "main_game", "matching", "fill_in", "odd_one_out", "final_challenge",
                            "collection"):
                pg.update(prompt=f"Nina and a {s.kind} scene number {k + 1}", illustration="opener")
            elif s.kind == "maze":
                pg["maze"] = {"start": "Nina waving", "goal": "a school"}
            elif s.kind == "solutions":
                pg["text"] = "Jeu 1 : chaud / froid"
            pages.append(pg)
    return {"title": "Nina à la plage", "author": "Anahita Darius", "type": "storybook", "language": "French",
            "style": "bright watercolor", "cover_prompt": "Nina on a beach", "trim": "8.5x8.5",
            "characters": [{"name": "Nina", "description": "a girl of seven, curly black hair, yellow dress"}],
            "learning": {"topic": "adjectifs", "marking": MARKING}, "sections": secs, "pages": pages,
            "back_cover": {"blurb": "Nina part à la plage."},
            "images": {"provider": "mock", "text_in_art": text_in_art}}


@pytest.mark.parametrize("lettered", [True, False])
def test_template_book_builds_40_pages(tmp_path, lettered):
    (tmp_path / "book.yaml").write_text(yaml.safe_dump(structured_book(lettered), allow_unicode=True))
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    m = build_interior(p)
    build_cover(p)
    report = check(p)
    assert report["ok"], report["errors"]
    assert m["pages"] == 40


def test_slots_per_kind():
    book = spec.Book.model_validate(structured_book(True))
    slots = {s.id: s for s in plan(book)}
    kinds = {s.kind for s in slots.values()}
    assert {"coloring", "observation", "maze_end"} <= kinds
    maze_n = next(i for i, pg in enumerate(book.pages, 1) if pg.kind == "maze")
    assert f"p{maze_n:03d}" not in slots and f"p{maze_n:03d}-start" in slots
    draw_n = next(i for i, pg in enumerate(book.pages, 1) if pg.kind == "guided_drawing")
    assert f"p{draw_n:03d}" not in slots
    story = slots["p002"]
    assert "[[" not in story.prompt and "«chaude (froide)»" in story.prompt and MARKING in story.prompt
    assert story.expected_text.endswith("La mer est chaude (froide).\nNina est petite (grande).")
    color = next(s for s in slots.values() if s.kind == "coloring")
    assert "Black-and-white line art" in color.prompt and "bright watercolor" not in color.prompt


def test_marks():
    assert spec.plain("a [[b (c)]] d") == "a b (c) d"
    assert spec.highlights("x [[un]] y [[deux]]") == ["un", "deux"]
    assert marked("a & [[b]]", "#123456") == 'a &amp; <font color="#123456">b</font>'
    with pytest.raises(ValueError):
        spec.Page(text="a [[b")


def test_structure_errors_and_brief_text():
    data = structured_book(True)
    assert author.structure_errors(data) == []
    data["pages"].pop(3)
    assert author.structure_errors(data)
    brief = {"idea": "x", "learning": {"topic": "adjectifs", "marking": MARKING, "explain": ""},
             "writing": {"inspired_by": "a playful rhyming author"},
             "structure": {"sections": structured_book(True)["sections"], "collection": "Nina va à l'école"}}
    text = author._brief_text(brief)
    assert "Interior pages: 40." in text and MARKING in text and "playful rhyming" in text
    assert "Nina va à l'école" in text and "explain" not in text


def test_written_book_gets_structure_and_learning(monkeypatch):
    book = structured_book(True)
    del book["sections"], book["learning"]

    async def fake_ask(prompt, system, schema=None, images=()):
        assert "[[double brackets]]" in system
        return "```yaml\n" + yaml.safe_dump(book, allow_unicode=True) + "```"
    monkeypatch.setattr(author, "ask", fake_ask)
    brief = {"idea": "x", "language": "French", "learning": {"topic": "adjectifs", "marking": MARKING},
             "structure": {"sections": structured_book(True)["sections"]}}
    out = yaml.safe_load(asyncio.run(author.write_book(brief, "outline", {"provider": "mock"})))
    assert out["learning"]["marking"] == MARKING and len(out["sections"]) == 18 and out["language"] == "French"
