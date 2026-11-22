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
            if s.kind == "matching":
                pg["matching"] = {"pairs": [["chaud", "froid"], ["petit", "grand"], ["haut", "bas"], ["jour", "nuit"]]}
            elif s.kind in ("fill_in", "main_game"):
                pg["fill_in"] = {"items": [{"prompt": "La mer est ___ .", "answer": "chaude"},
                                           {"prompt": "Le contraire de petit est ___ .", "answer": "grand"},
                                           {"prompt": "Écris une phrase avec « grand ».", "answer": "Le château est grand."}]}
            elif s.kind == "odd_one_out":
                pg["odd_one_out"] = {"groups": [{"items": ["chat", "chien", "pomme", "lapin"], "answer": "pomme"},
                                                {"items": ["2", "4", "7", "8"], "answer": "7"}]}
            elif s.kind == "final_challenge":
                pg["certificate"] = {"title": "Bravo !", "name_label": "Prénom", "date_label": "Date"}
                pg.pop("prompt", None)
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


def test_game_data_has_exactly_one_answer():
    with pytest.raises(ValueError):  # two identical right items: more than one correct pairing
        spec.MatchingSpec(pairs=[["a", "x"], ["b", "x"]])
    with pytest.raises(ValueError):  # the answer is not in the group
        spec.OddGroup(items=["chat", "chien", "lapin"], answer="pomme")
    page = spec.Page(kind="matching", matching={"pairs": [["a", "b"], ["c", "d"]]})
    assert page.drawn_activity and not spec.Page(kind="matching").drawn_activity


def test_games_never_go_to_the_image_model_and_need_their_data():
    data = structured_book(True)
    book = spec.Book.model_validate(data)
    slots = {s.id: s for s in plan(book)}
    for n, pg in enumerate(book.pages, 1):
        if pg.drawn_activity:
            assert not book.lettered(pg)
            s = slots.get(f"p{n:03d}")
            assert s is None or (s.kind == "maze_end" and not s.lettering)
    assert author.activity_errors(data) == []
    del next(pg for pg in data["pages"] if pg["kind"] == "matching")["matching"]
    assert author.activity_errors(data)


def test_solutions_come_from_the_games(tmp_path):
    from bookforge.layout.activities import answers, derangement
    from bookforge.layout.base import Sheet, theme_for
    book = spec.Book.model_validate(structured_book(False))
    sheet = Sheet(tmp_path / "x.pdf", (8.5, 8.5), tmp_path, theme_for(book))
    text = " ".join(getattr(f, "text", "") for b in answers(sheet, book) for f in getattr(b, "parts", [b]))
    assert "chaud&nbsp;—&nbsp;froid" in text and "pomme" in text and "grand" in text
    for n in range(2, 9):
        assert all(o != i for i, o in enumerate(derangement(n, n)))


def test_text_is_set_on_the_frames_empty_paper_never_on_its_drawing(tmp_path):
    """A generated frame whose character reaches into the middle: the words go around it, and preflight
    fails a text box laid over the drawing."""
    from PIL import Image, ImageDraw
    from bookforge import kdp
    from bookforge.imaging import calm
    from bookforge.layout import shaped
    from bookforge.layout.base import Sheet, frame_box, theme_for
    from bookforge.layout.storybook import back_matter
    from bookforge.preflight import text_on_drawing
    (tmp_path / "book.yaml").write_text(yaml.safe_dump(structured_book(False), allow_unicode=True))
    p = Project(tmp_path / "book.yaml", mock=True)
    i = kdp.Interior(*p.book.trim_size, 40)
    art = p.art_path("text-frame")
    art.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (850, 850), "#FFF8EC")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 850, 110], fill="#5AB0F0")                # sky along the top
    d.rectangle([0, 740, 850, 850], fill="#4CAF50")              # meadow along the bottom
    d.ellipse([60, 60, 380, 380], fill="#E05A9A")                # a character reaching into the middle
    im.save(art)
    (bx, by, bw, bh), panel = frame_box(i, 3, art)
    assert not panel and calm.busy_fraction(art, i.page_w, i.page_h, (bx, by, bw, bh)) == 0
    # the top-left of the old fixed box (76% x 80% of the page) sat on the character
    assert calm.busy_fraction(art, i.page_w, i.page_h, (i.page_w * 0.12 + 0.3, i.page_h * 0.9 - 2.3, 2, 2)) > 0.3
    sheet = Sheet(tmp_path / "x.pdf", (i.page_w, i.page_h), tmp_path, theme_for(p.book))
    page = next(pg for pg in p.book.pages if pg.kind == "solutions")
    shape = calm.shape_of(art, i.page_w, i.page_h)
    assert shaped.place(sheet, back_matter(sheet, p.book, page, 0.8)[:2], shape, i.safe_box(3), art=art.name)
    errors = []
    text_on_drawing(p, i, sheet.records["text"], errors)
    assert not errors
    text_on_drawing(p, i, [{"page": 3, "box": [1.0, 5.5, 2.5, 1.5], "art": art.name}], errors)
    assert errors and "over the picture" in errors[0]


@pytest.mark.parametrize("lettered", [True, False])
def test_control_knows_the_words_of_exercise_and_solutions_pages(tmp_path, lettered):
    """A wording fix on a game or the solutions page edits book.yaml, never redraws the vignette or frame."""
    from bookforge import control
    raw = yaml.safe_dump(structured_book(lettered), allow_unicode=True)
    (tmp_path / "book.yaml").write_text(raw)
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p)
    build_interior(p)
    info = control.page_info(p)
    kinds = {n: [p.book.pages[b - 1].kind for b in i["book_pages"]] for n, i in info.items()}
    game = next(n for n, k in kinds.items() if "odd_one_out" in k)
    sol = next(n for n, k in kinds.items() if "solutions" in k)
    assert "odd_one_out group 1" in info[game]["text"] and "'pomme'" in info[game]["text"]
    assert "answers from book.yaml page" in info[sol]["text"] and "'pomme'" in info[sol]["text"]
    for n in (game, sol):
        issue = control._normalise({"page": n, "problem": "typo", "current": "pomme", "replace_with": "poire",
                                    "fix": "text", "prompt": "Write poire."}, info)
        assert issue["fix"] == "text" and issue["slot"] is None
        out = control._direct(raw, issue)  # item and answer both change; nothing else in the book does
        group = yaml.safe_load(out)["pages"][info[game]["book_pages"][0] - 1]["odd_one_out"]["groups"][0]
        assert group["answer"] == "poire" and "poire" in group["items"] and "pomme" not in out
    # words that are also printed elsewhere are left to Claude, which is told where to look
    assert control._direct(raw, {**issue, "current": "Nina", "replace_with": "Nora"}) is None


CONJUGATION = """Être, avoir, chanter, danser, voler.

| | être | avoir | chanter | danser | voler |
|---|---|---|---|---|---|
| je | j'étais | j'avais | chantais | dansais | volais |
| nous | étions | avions | chantions | dansions | volions |
| ils/elles | étaient | avaient | chantaient | dansaient | volaient |"""



@pytest.mark.parametrize("width", [2.2, 3.0, 4.2, 6.4])
def test_table_cells_never_cut_a_word(tmp_path, width):
    """A six-column verb table on a narrow page printed "chantio / ns": each column now holds its longest
    word whole (the font shrinks first), and the page layout never squeezes it below that width."""
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from bookforge.layout import tables
    from bookforge.layout.base import Sheet, theme_for
    book = spec.Book.model_validate(structured_book(False))
    sheet = Sheet(tmp_path / "x.pdf", (8.5, 8.5), tmp_path, theme_for(book))
    table = next(f for f in tables.learning_page(sheet, CONJUGATION) if isinstance(f, tables.TableBlock))
    assert table.min_w < table.want <= table.max_w
    w = max(width, table.min_w)  # shaped.place never gives a table less than its min_w
    size, widths = table._layout(w * inch)
    assert sum(widths) <= w * inch + 0.5 and size >= table.MIN_SIZE
    pad = 2 * table.PAD
    for i, r in enumerate(table.rows):
        font = sheet.theme.heading if i == 0 else sheet.theme.body
        for c, cw in zip(r, widths):
            for x in c.split():
                assert stringWidth(x, font, size) + pad <= cw + 0.01, f"{x!r} cut at {w} in"


def test_cut_word_in_a_table_is_fixed_by_a_rebuild_not_a_yaml_edit(tmp_path):
    """Control's Apply on a layout problem of a page with a table must not ask Claude to edit book.yaml (the
    table's columns come from the layout code); a wording fix or a layout problem elsewhere still does."""
    from bookforge import control
    raw = structured_book(False)
    ref = next(pg for pg in raw["pages"] if pg["kind"] == "reference")
    ref["text"] = CONJUGATION
    (tmp_path / "book.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True))
    p = Project(tmp_path / "book.yaml", mock=True)
    n = raw["pages"].index(ref) + 1
    other = next(k for k, pg in enumerate(raw["pages"], 1) if pg["kind"] == "story")
    issue = {"fix": "layout", "book_pages": [n], "book_page": n, "replace_with": ""}
    assert control.is_table_layout(p, issue)
    assert not control.is_table_layout(p, {**issue, "fix": "text"})
    assert not control.is_table_layout(p, {**issue, "replace_with": "chantions"})
    assert not control.is_table_layout(p, {**issue, "book_pages": [other], "book_page": other})


def test_full_translation_finds_what_teaches_and_what_breaks():
    """Step 1 and the structure check of a full translation (bookforge/translate.py)."""
    from bookforge import translate
    data = structured_book(False)
    ctx = translate.context(data)
    kinds = {data["pages"][int(p["where"].split(".")[1])].get("kind") for p in ctx["pages"]}
    assert ctx["learning"]["marking"] == MARKING
    assert {"story", "matching", "fill_in", "odd_one_out", "main_game"} <= kinds  # marked story pages count too
    assert not kinds & {"maze", "coloring", "copyright", "collection"}
    assert translate.context({"title": "x", "pages": [{"text": "a fox", "prompt": "a fox"}]}) == {}
    assert translate.label(data, ctx["pages"][-1]["where"]).startswith("Page ")

    texts = translate.texts(data)
    assert translate.fits(data, texts) == []
    game = next(i for i, p in enumerate(data["pages"]) if p.get("matching"))
    odd = next(i for i, p in enumerate(data["pages"]) if p.get("odd_one_out"))
    # two words that become the same word in the new language: two right answers, the game breaks
    clash = {**texts, f"pages.{game}.matching.pairs.0.0": "hot", f"pages.{game}.matching.pairs.1.0": "hot"}
    assert any("matching" in e for e in translate.fits(data, clash))
    clash = {**texts, f"pages.{odd}.odd_one_out.groups.0.items.0": "pet", f"pages.{odd}.odd_one_out.groups.0.items.1": "pet"}
    assert any("odd_one_out" in e for e in translate.fits(data, clash))
    view = yaml.safe_load(translate.teaching_view(data, texts, ctx))
    assert view["learning"]["marking"] == MARKING and any(p.get("odd_one_out") for p in view["pages"])


@pytest.mark.parametrize("fixed", [True, False])
def test_full_translation_adapts_then_playtests(monkeypatch, fixed):
    """Steps 2-4: Claude adapts, a play-test checks, its findings go back once more; what stays broken is reported."""
    from bookforge import translate
    data = structured_book(False)
    ctx = translate.context(data)
    texts = translate.texts(data)
    odd = next(f"pages.{i}" for i, p in enumerate(data["pages"]) if p.get("odd_one_out"))
    prompts = []

    async def fake_ask(prompt, system, schema=None, images=()):
        prompts.append(prompt)
        if schema is author.PLAYTEST_SCHEMA:
            assert "[EN]" in prompt  # the tester reads the translated book
            bad = not fixed or not any(s is author.PLAYTEST_SCHEMA for s in kinds)  # the first play-test fails
            kinds.append(schema)
            return {"problems": [{"where": odd, "problem": "Two items are fruit in English."}] if bad else []}
        kinds.append(schema)
        return {"items": [{"id": k, "text": f"[EN] {v}"} for k, v in texts.items()],
                "adapted": [{"where": odd, "change": "New groups: the French ones hinged on gender."}]}
    kinds = []
    monkeypatch.setattr(author, "ask", fake_ask)
    out = asyncio.run(author.translate_full(texts, "English", "French",
                                            lambda o, t: translate.check(o, t) + translate.fits(data, t), ctx,
                                            lambda t: translate.teaching_view(data, t, ctx)))
    assert out["texts"]["title"] == "[EN] Nina à la plage"
    assert out["adapted"] == [{"where": odd, "change": "New groups: the French ones hinged on gender."}]
    assert "Teaching parts" in prompts[0] and "Two items are fruit in English." in prompts[2]
    if fixed:
        assert out["unresolved"] == [] and len(prompts) == 4
    else:  # three rounds at most, then what is still wrong is handed to the user instead of failing
        assert out["unresolved"][0]["where"] == odd and len(prompts) == 6


def test_full_translation_asks_before_translating(monkeypatch):
    """Claude names the learning points that break in the new language and asks how each should work;
    the author's answers then go into the translation itself."""
    from bookforge import translate
    data = structured_book(False)
    ctx = translate.context(data)
    texts = translate.texts(data)
    odd = next(f"pages.{i}" for i, p in enumerate(data["pages"]) if p.get("odd_one_out"))
    seen = []

    async def fake_ask(prompt, system, schema=None, images=()):
        seen.append(prompt)
        if schema is author.TRANSLATION_PLAN_SCHEMA:
            assert "Teaching parts" in prompt and MARKING in prompt
            return {"questions": [{"id": "", "where": "learning", "issue": "French adjectives agree; English ones do not.",
                                   "question": "What should the adjective lesson teach in English?",
                                   "options": ["Opposites (hot / cold)", "  ", "Comparatives (big / bigger)"]}] * 8,
                    "auto": [{"where": odd, "change": "New groups, the French ones hinged on gender."}, {"where": odd, "change": " "}]}
        if schema is author.PLAYTEST_SCHEMA:
            return {"problems": []}
        return {"items": [{"id": k, "text": f"[EN] {v}"} for k, v in texts.items()], "adapted": []}
    monkeypatch.setattr(author, "ask", fake_ask)
    plan = asyncio.run(author.translation_plan(texts, "English", "French", ctx))
    assert len(plan["questions"]) == 6 and plan["questions"][0]["id"] == "q1"  # at most 6, each with an id
    assert plan["questions"][0]["options"] == ["Opposites (hot / cold)", "Comparatives (big / bigger)"]
    assert plan["auto"] == [{"where": odd, "change": "New groups, the French ones hinged on gender."}]

    q = plan["questions"][0]
    asyncio.run(author.translate_full(texts, "English", "French", lambda o, t: [], ctx,
                                      lambda t: translate.teaching_view(data, t, ctx),
                                      [{"where": "learning", "question": q["question"], "answer": "Comparatives (big / bigger)"},
                                       {"where": odd, "question": "Keep the groups?", "answer": ""}]))
    sent = seen[-2]  # the translation prompt, before the play-test
    assert "Follow every answer exactly" in sent and "-> Comparatives (big / bigger)" in sent
    assert "Keep the groups? -> no answer: you decide" in sent
