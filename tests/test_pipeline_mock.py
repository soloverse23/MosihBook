"""End-to-end runs with the mock provider: every book type must pass preflight."""
import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bookforge import spec, storymd
from bookforge.art import generate
from bookforge.layout.cover import build_cover
from bookforge.layout.render import build_interior
from bookforge.plan import plan
from bookforge.preflight import check
from bookforge.project import Project

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize("name", ["picture-book", "storybook", "comic"])
def test_example_builds_and_passes_preflight(tmp_path, name):
    shutil.copy(EXAMPLES / name / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    m = build_interior(p)
    build_cover(p)
    report = check(p)
    assert report["ok"], report["errors"]
    assert m["pages"] % 2 == 0 and m["pages"] >= 24


def test_spreads_start_on_verso(tmp_path):
    shutil.copy(EXAMPLES / "picture-book" / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    m = build_interior(p)
    spread_pages = sorted(i["page"] for i in m["images"] if i["src"] in ("p001.png", "p008.png", "p014.png"))
    for left, right in zip(spread_pages[::2], spread_pages[1::2]):
        assert left % 2 == 0 and right == left + 1


def test_regen_changes_only_requested_slot(tmp_path):
    shutil.copy(EXAMPLES / "comic" / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    before = {f.name: f.read_bytes() for f in p.art.glob("*.png")}
    cache_count = len(list(p.cache.glob("*.png")))
    generate.run(p, {"p001"}, bump={"p001"})
    assert len(list(p.cache.glob("*.png"))) == cache_count + 1
    after = {f.name: f.read_bytes() for f in p.art.glob("*.png")}
    assert {k for k in before if before[k] != after[k]} <= {"p001.png"}


def test_prompts_carry_style_characters_and_no_text_rule():
    book = spec.load(EXAMPLES / "picture-book" / "book.yaml")
    book.images.text_in_art = False
    slot = next(s for s in plan(book) if s.id == "p007")
    assert book.style.split()[0] in slot.prompt
    assert "Grandma Owl" in slot.characters and "Pip" in slot.characters
    assert "Absolutely no text" in slot.prompt


def test_lettered_prompts_carry_the_exact_words_and_lettering():
    book = spec.load(EXAMPLES / "picture-book" / "book.yaml")
    slots = {s.id: s for s in plan(book)}
    page = slots["p002"]
    assert book.pages[1].text.strip() in page.prompt and book.lettering in page.prompt
    assert "Absolutely no text" not in page.prompt and "TEXT TO LETTER" in page.prompt
    assert page.expected_text == book.pages[1].text.strip()
    cover = slots["cover-front"]
    assert book.title in cover.prompt and book.author in cover.prompt
    assert "barcode" in slots["cover-back"].prompt and book.back_cover.blurb.split()[0] in slots["cover-back"].prompt
    assert "the-end" in slots and "text-frame" not in slots  # no long text-only pages in this book


def test_lettered_book_has_no_typeset_story_text(tmp_path):
    p = _storybook(tmp_path)
    generate.run(p)
    m = build_interior(p)
    story = {i["page"] for i in m["images"] if i["src"].startswith("p0")}
    framed = {i["page"] for i in m["images"] if i["src"] == "text-frame.png"}
    assert story and framed and not story & {t["page"] for t in m["text"] if not t.get("folio")}
    assert {t["page"] for t in m["text"] if t["page"] in framed}  # the glossary is typeset inside the frame
    assert story <= {t["page"] for t in m["text"] if t.get("folio")}  # page numbers on the picture pages
    c = build_cover(p)
    assert c["text"] == []  # title, author and blurb are in the art
    assert check(p)["ok"]


def test_unknown_character_rejected():
    data = yaml.safe_load((EXAMPLES / "comic" / "book.yaml").read_text())
    data["pages"][0]["characters"] = ["Nobody"]
    with pytest.raises(ValidationError):
        spec.Book.model_validate(data)


def test_storymd_roundtrip():
    md = "title: T\nauthor: A\nstyle: ink\ncover_prompt: c\n---\nHello there.\n> prompt: a cat\n> layout: spot\n---\nBye."
    book = spec.Book.model_validate(yaml.safe_load(storymd.convert(md)))
    assert book.pages[0].prompt == "a cat" and book.pages[0].layout == "spot"
    assert book.pages[1].text == "Bye."


def test_high_quality_slot_gets_its_own_cache_entry(tmp_path):
    shutil.copy(EXAMPLES / "comic" / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    n = len(list(p.cache.glob("*.png")))
    p.book.images.high_quality = ["p001"]
    generate.run(p)
    assert len(list(p.cache.glob("*.png"))) == n + 1  # only the high slot is redone


def _storybook(tmp_path, edit=None):
    data = yaml.safe_load((EXAMPLES / "storybook" / "book.yaml").read_text())
    if edit:
        edit(data)
    (tmp_path / "book.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return Project(tmp_path / "book.yaml", mock=True)


def test_storybook_pictures_carry_their_text(tmp_path):
    """Books without text_in_art: typeset words on a panel over the picture, on the same page."""
    # too long for a panel on the art: the page falls back to art on top, text below, still one page
    long = "\n".join(f"Line {i} of a long page that a child reads." for i in range(18))
    p = _storybook(tmp_path, lambda d: d.pop("images") and d["pages"].append(
        {"prompt": "Ada waving goodbye at the tower door", "characters": ["Ada"], "illustration": "opener", "text": long}))
    generate.run(p)
    m = build_interior(p)
    text_pages = {t["page"] for t in m["text"]}
    story_art = [i for i in m["images"] if i["src"].startswith("p0")]
    assert len(story_art) == len([x for x in p.book.pages if x.prompt])
    for img in story_art:  # never a picture page followed by a text page
        assert img["page"] in text_pages, img
    build_cover(p)
    assert check(p)["ok"]


def test_characters_are_locked_and_reused(tmp_path):
    p = _storybook(tmp_path)
    generate.run(p)
    entry = p.characters / "ada"
    assert (entry / "sheet.png").exists()
    assert yaml.safe_load((entry / "character.yaml").read_text())["name"] == "Ada"

    # a changed description does not change the look: the locked wording and sheet are used
    p = _storybook(tmp_path, lambda d: d["characters"][0].update(description="a tall boy in a red cap"))
    lines = []
    generate.run(p, log=lines.append)
    assert any("Ada" in line and "locked" in line for line in lines)
    page = next(s for s in plan(p.book) if s.id == "p001")
    assert "long dark braid" in page.prompt and "red cap" not in page.prompt

    from bookforge import characters
    assert characters.reset(p, "Ada") and not (entry / "sheet.png").exists()
    p = _storybook(tmp_path, lambda d: d["characters"][0].update(description="a tall boy in a red cap"))
    generate.run(p)
    assert "red cap" in yaml.safe_load((entry / "character.yaml").read_text())["description"]


def test_preflight_blocks_misspelled_lettering(tmp_path):
    import json
    shutil.copy(EXAMPLES / "picture-book" / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    build_interior(p)
    build_cover(p)
    assert check(p)["ok"]
    f = p.build / "review-mock.json"
    reviews = json.loads(f.read_text())
    key = reviews["_chosen"]["p002"]["key"]
    reviews[key]["verdict"]["text_errors"] = ["'Wilowmere' should be 'Willowmere'"]
    f.write_text(json.dumps(reviews))
    report = check(p)
    assert not report["ok"] and any("p002" in e and "Wilowmere" in e for e in report["errors"])


def test_page_numbers_can_be_switched_off(tmp_path):
    p = _storybook(tmp_path)
    p.book.page_numbers = False
    generate.run(p)
    m = build_interior(p)
    assert not [t for t in m["text"] if t.get("folio")]
