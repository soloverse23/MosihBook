"""Studio end to end with Claude stubbed out: brief -> questions -> outline -> book.yaml -> mock build -> zip."""
import io
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from bookforge import author, settings
from bookforge.web import app as webapp
from bookforge.web import state

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "picture-book" / "book.yaml"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PATH", tmp_path / "home" / "settings.json")
    settings.save({"books_dir": str(tmp_path / "books"), "openai_api_key": "sk-test-1234567890abcd"})

    async def questions(brief, refs="", images=()):
        if refs:
            return [{"id": "ref", "question": refs}]
        return [{"id": "hero", "question": "Who is the hero?", "options": ["a fox", "an owl"]}]

    async def outline(brief, qs, answers, feedback="", previous="", refs="", images=()):
        return f"## Title\n- Pip\n\nhero: {answers.get('hero')}"

    async def write_book(brief, outline_md, image_block, refs="", images=()):
        return EXAMPLE.read_text()

    async def listing(text, pages):
        return {"description": "A fox.", "keywords": ["fox"] * 7, "categories": ["Kids"], "reading_age": "3-6",
                "suggested_price_usd": 11.99, "price_reasoning": "", "ai_disclosure": "Images are AI-generated."}

    for name, fn in [("questions", questions), ("outline", outline), ("write_book", write_book), ("listing", listing)]:
        monkeypatch.setattr(author, name, fn)
    return TestClient(webapp.app)


def _wait(client, job_id):
    for _ in range(300):
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] != "running":
            return j
        time.sleep(0.2)
    raise TimeoutError


def test_brief_attachments_reach_claude(client):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "The fox is called Juniper and lives under the old oak.")
    c.save()
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox"}).json()["slug"]
    r = client.post(f"/api/books/{slug}/sources?name=notes.pdf", content=buf.getvalue())
    assert r.status_code == 200 and r.json()["chars"] > 20
    assert client.post(f"/api/books/{slug}/sources?name=more.md", content="Juniper loves stars".encode()).status_code == 200
    assert client.post(f"/api/books/{slug}/sources?name=x.exe", content=b"MZ").status_code == 400
    assert [s["name"] for s in client.get(f"/api/books/{slug}").json()["sources"]] == ["more.md", "notes.pdf"]

    q = client.post(f"/api/books/{slug}/claude/questions").json()["questions"][0]["question"]
    assert "=== notes.pdf ===" in q and "Juniper and lives under the old oak" in q and "loves stars" in q

    assert [s["name"] for s in client.delete(f"/api/books/{slug}/sources/notes.pdf").json()["sources"]] == ["more.md"]


def test_wizard_mock_build_and_download(client):
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox and the stars"}).json()["slug"]
    qs = client.post(f"/api/books/{slug}/claude/questions").json()["questions"]
    assert qs[0]["id"] == "hero"
    st = client.post(f"/api/books/{slug}/claude/outline", json={"answers": {"hero": "a fox"}}).json()
    assert "a fox" in st["outline"] and st["step"] == "outline"
    assert client.post(f"/api/books/{slug}/claude/write", json={}).json()["step"] == "manuscript"

    book = client.get(f"/api/books/{slug}").json()
    assert book["yaml_error"] is None and book["pages_view"][0]["text"].startswith("In the woods")
    assert client.get(f"/api/books/{slug}/plan").json()["slots"]

    job = client.post(f"/api/books/{slug}/jobs/mock").json()["job"]
    j = _wait(client, job)
    assert j["status"] == "done", j["lines"]
    assert j["result"]["preflight"]["ok"]
    assert client.get(f"/api/books/{slug}/build/preview.html").status_code == 200
    assert client.get(f"/api/books/{slug}/build/../book.yaml").status_code == 404

    proofs = client.get(f"/api/books/{slug}/proofs").json()
    assert proofs["cover"] and proofs["pages"][0] == "page-001.png"
    review = client.get(f"/api/books/{slug}/review").json()
    assert review["mock"] and review["slots"] and all(s["ok"] for s in review["slots"])
    assert client.get(f"/api/books/{slug}/build/{review['slots'][0]['thumb']}").status_code == 200
    assert client.get(f"/api/books/{slug}").json()["files"]["interior.pdf"] > 0

    summary = next(b for b in client.get("/api/books").json() if b["slug"] == slug)
    assert summary["status"] == "mock preview"

    client.post(f"/api/books/{slug}/listing")
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/books/{slug}/download.zip").content))
    assert {"interior.pdf", "cover.pdf", "book.yaml", "kdp-listing.md"} <= set(z.namelist())


def test_invalid_yaml_is_rejected_unless_forced(client):
    slug = client.post("/api/books", json={"idea": "x"}).json()["slug"]
    assert client.put(f"/api/books/{slug}/yaml", json={"yaml": "title: only"}).status_code == 422
    r = client.put(f"/api/books/{slug}/yaml", json={"yaml": "title: only", "save_invalid": True}).json()
    assert r["yaml_error"]


def test_settings_never_return_full_keys(client):
    s = client.get("/api/settings").json()["settings"]
    assert s["openai_api_key"] != "sk-test-1234567890abcd" and s["openai_api_key"].endswith("abcd")
    # sending the masked value back keeps the real key
    client.put("/api/settings", json={**s, "default_author": "Me"})
    assert settings.load().openai_api_key == "sk-test-1234567890abcd"
    assert settings.load().default_author == "Me"
    assert (settings.PATH.stat().st_mode & 0o777) == 0o600


def test_real_art_needs_openai_key(client):
    settings.save({"openai_api_key": ""})
    slug = client.post("/api/books", json={"idea": "x"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    assert client.post(f"/api/books/{slug}/jobs/art").status_code == 400


def test_unknown_book_and_bad_slug_404(client):
    assert client.get("/api/books/nope").status_code == 404
    assert client.get("/api/books/..%2Fetc/build/x").status_code == 404


def test_high_quality_toggle_changes_estimate(client):
    slug = client.post("/api/books", json={"idea": "x"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    before = client.get(f"/api/books/{slug}/plan").json()
    assert before["quality"] == "medium" and all(s["quality"] == "medium" for s in before["slots"])
    after = client.put(f"/api/books/{slug}/high", json={"slots": ["cover-front"], "on": True}).json()
    cover = next(s for s in after["slots"] if s["id"] == "cover-front")
    assert cover["quality"] == "high"
    assert round(after["estimate_usd"] - before["estimate_usd"], 2) == round(after["high_cost_usd"] - after["base_cost_usd"], 2)
    off = client.put(f"/api/books/{slug}/high", json={"slots": ["cover-front"], "on": False}).json()
    assert off["estimate_usd"] == before["estimate_usd"]


def test_character_library_and_cast_reach_claude(client, tmp_path):
    from bookforge import characters
    lib = characters.library_dir()
    assert lib.is_relative_to(tmp_path)  # tests never touch the real library
    (lib / "pip").mkdir(parents=True)
    (lib / "pip" / "character.yaml").write_text("name: Pip\ndescription: a small red fox kit\nsource_book: Book One\n")
    from PIL import Image
    Image.new("RGB", (8, 8), "red").save(lib / "pip" / "sheet.png")
    assert [c["name"] for c in client.get("/api/characters").json()["characters"]] == ["Pip"]
    assert client.get("/api/characters/pip.png").status_code == 200
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buf, "PNG")
    assert client.post("/api/characters/pip/sheet", content=buf.getvalue()).status_code == 200
    assert client.post("/api/characters/pip/sheet", content=b"not an image").status_code == 400
    assert client.get("/api/characters/..%2Fsettings.json.png").status_code == 404
    assert "a small red fox kit" in author._brief_text({"idea": "x", "cast": ["Pip"]})
    assert client.delete("/api/characters/pip").json()["characters"] == []


def test_brief_image_attachment(client, monkeypatch):
    import asyncio
    from PIL import Image
    from bookforge.web import state
    buf = io.BytesIO()
    Image.new("RGB", (3000, 2000), "orange").save(buf, "PNG")
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox"}).json()["slug"]
    assert client.post(f"/api/books/{slug}/sources?name=sketch.png", content=buf.getvalue()).status_code == 200
    assert client.post(f"/api/books/{slug}/sources?name=bad.png", content=b"not an image").status_code == 400
    assert [p.name for p in state.source_images(slug)] == ["sketch.png"]
    assert "sketch.png" in state.sources_text(slug)

    async def first(gen):
        return [m async for m in gen][0]
    msg = asyncio.run(first(author._with_images("hello", state.source_images(slug))))
    content = msg["message"]["content"]
    assert content[1]["type"] == "image" and content[1]["source"]["media_type"] == "image/jpeg"
    assert content[-1] == {"type": "text", "text": "hello"}


def test_login_gate(client, monkeypatch):
    monkeypatch.setenv("MOSIBOOKS_PASSWORD", "s3cret")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login"
    assert client.get("/api/books").status_code == 401
    assert client.get("/login").status_code == 200
    assert client.post("/api/login", json={"username": "admin", "password": "nope"}).status_code == 401
    assert client.post("/api/login", json={"username": "admin", "password": "s3cret"}).status_code == 200
    assert client.get("/api/books").status_code == 200
    assert client.get("/", follow_redirects=False).status_code == 200
    client.post("/api/logout")
    assert client.get("/api/books").status_code == 401


def test_no_password_means_open(client, monkeypatch):
    monkeypatch.delenv("MOSIBOOKS_PASSWORD", raising=False)
    assert client.get("/api/books").status_code == 200


def test_first_run_setup(client, monkeypatch, tmp_path):
    settings.save({"openai_api_key": "", "onboarded": False})
    assert client.get("/api/setup").json()["onboarded"] is False
    assert client.post("/api/setup/done").json()["ok"]
    assert client.get("/api/setup").json()["onboarded"] is True


def test_templates_api(client):
    r = client.get("/api/templates").json()
    anahita = next(t for t in r["templates"] if t["id"] == "anahita-40")
    assert anahita["pages"] == 40 and anahita["builtin"] and not anahita["saved"] and "maze" in r["kinds"]
    t = client.post("/api/templates", json={"name": "Short book", "sections": [{"kind": "story", "pages": 12},
                                                                             {"kind": "coloring", "pages": 2}]}).json()
    assert t["id"] == "short-book" and t["pages"] == 14
    assert client.post("/api/templates", json={"name": "Bad", "sections": [{"kind": "karaoke"}]}).status_code == 422
    assert client.delete("/api/templates/short-book").status_code == 200
    assert client.delete("/api/templates/anahita-40").status_code == 404  # built-in, nothing saved


def test_template_draft_from_prompt(client, monkeypatch):
    seen = {}

    async def ask(prompt, system, schema=None, images=()):
        seen["prompt"] = prompt
        return {"name": "Mini", "description": "Short.", "sections": [
            {"kind": "parents_note", "pages": 1, "title": ""}, {"kind": "story", "pages": 99}, {"kind": "karaoke", "pages": 1}]}

    monkeypatch.setattr(author, "ask", ask)
    assert client.post("/api/templates/draft", json={"prompt": " "}).status_code == 422
    r = client.post("/api/templates/draft", json={"prompt": "maze after the story",
                                                  "current": {"name": "Old", "sections": [{"kind": "story", "pages": 10}]}}).json()
    assert r["sections"] == [{"kind": "parents_note", "pages": 1}, {"kind": "story", "pages": 60}]  # unknown kind dropped, pages capped
    assert "maze after the story" in seen["prompt"] and '"story"' in seen["prompt"]
    # an edited built-in is saved as the writer's own copy under the same id, with its new name
    t = client.post("/api/templates", json={"id": "anahita-40", "name": "Renamed", "sections": r["sections"]}).json()
    got = next(x for x in client.get("/api/templates").json()["templates"] if x["id"] == "anahita-40")
    assert got["name"] == "Renamed" and got["saved"] and t["pages"] == 61


def test_job_reports_each_image_live(client):
    slug = client.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    job = client.post(f"/api/books/{slug}/jobs/mock").json()["job"]
    assert client.get(f"/api/books/{slug}").json()["job_kind"] in ("mock", None)  # refresh can find the job
    for _ in range(300):
        j = client.get(f"/api/jobs/{job}").json()
        if j["status"] != "running":
            break
        time.sleep(0.1)
    pg = j["progress"]
    assert j["status"] == "done" and pg["total"] > 0 and pg["done"] == pg["total"] and not pg["active"]
    first = pg["images"][0]["id"]
    assert client.get(f"/api/books/{slug}/build/thumbs/{first}.jpg").status_code == 200


def test_claude_bin_finds_the_windows_binary(tmp_path, monkeypatch):
    import shutil
    import sys
    import types

    from bookforge.web import app as web_app
    (tmp_path / "_bundled").mkdir()
    (tmp_path / "_bundled" / "claude.exe").touch()
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", types.SimpleNamespace(__file__=str(tmp_path / "__init__.py")))
    assert web_app._claude_bin() == str(tmp_path / "_bundled" / "claude.exe")


def test_page_numbers_toggle_reaches_a_written_book(client):
    import yaml
    slug = client.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    client.put(f"/api/books/{slug}/state", json={"brief": {"idea": "a fox", "page_numbers": False}})
    assert yaml.safe_load(client.get(f"/api/books/{slug}").json()["yaml"])["page_numbers"] is False
    client.put(f"/api/books/{slug}/state", json={"brief": {"idea": "a fox", "page_numbers": True}})
    assert yaml.safe_load(client.get(f"/api/books/{slug}").json()["yaml"])["page_numbers"] is True


@pytest.mark.parametrize("lettered", [False, True])
def test_translate_keeps_the_art(client, monkeypatch, lettered):
    import json
    import shutil

    import yaml

    from bookforge import translate
    data = yaml.safe_load(EXAMPLE.read_text())
    data["images"]["text_in_art"] = lettered
    slug = client.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": yaml.safe_dump(data, allow_unicode=True)})
    assert client.post(f"/api/books/{slug}/translate", json={"language": "French"}).status_code == 400  # no art yet
    assert _wait(client, client.post(f"/api/books/{slug}/jobs/mock").json()["job"])["status"] == "done"
    build = Path(settings.load().books_dir) / slug / "build"
    shutil.copytree(build / "art-mock", build / "art")  # stand-in for the paid art
    shutil.copy(build / "review-mock.json", build / "review.json")
    shutil.copytree(build / "characters-mock", build.parent / "characters")

    async def fake(texts, language, source, check):
        out = {k: f"[FR] {v}" if "[[" not in v else v for k, v in texts.items()}
        assert not check(texts, out)
        return out
    monkeypatch.setattr(author, "translate", fake)
    r = client.post(f"/api/books/{slug}/translate", json={"language": "French"}).json()
    new = Path(settings.load().books_dir) / r["slug"]
    book = yaml.safe_load((new / "book.yaml").read_text())
    assert book["language"] == "French" and book["title"].startswith("[FR]")
    assert all(p["text"].startswith("[FR]") for p in book["pages"] if p.get("text") and "[[" not in p["text"])
    assert {p.name for p in (new / "characters").iterdir()} == {p.name for p in (build.parent / "characters").iterdir()}
    kept = sorted(p.stem for p in (new / "build" / "art").glob("*.png"))
    assert kept == sorted(r["reused"]) and set(json.loads((new / "build" / "review.json").read_text())["_chosen"]) == set(kept)
    if lettered:  # the words are in the pictures: those pages and the cover are drawn again
        assert "cover-front" in r["redraw"] and any(s.startswith("p0") for s in r["redraw"]) and r["redraw_cost_usd"] > 0
        assert "the-end" in r["redraw"]  # "The End" is lettered again as "Fin", never reused in English
    else:  # nothing to draw: the translated book builds straight away from the same art
        assert r["redraw"] == [] and r["reused"]
        from bookforge.art import generate
        from bookforge.project import Project

        class NoSpend:
            model = "x"
            def request_size(self, aspect): return (1024, 1024)
            def generate(self, *a): raise AssertionError("a reused image was drawn again")
        monkeypatch.setattr(generate, "get_provider", lambda s: NoSpend())
        monkeypatch.setattr(generate, "get_reviewer", lambda s: None)
        assert generate.run(Project(new / "book.yaml"), log=lambda m: None) == {}  # nothing flagged "page changed"
        j = _wait(client, client.post(f"/api/books/{r['slug']}/jobs/build").json()["job"])
        assert j["status"] == "done", j["lines"]
    assert translate.check({"a": "x [[y]]"}, {"a": "x y"})  # a lost highlight is caught

    # the library shows the translation right after its original, tagged with both languages
    books = client.get("/api/books").json()
    at = [b["slug"] for b in books].index(slug)
    assert books[at]["editions"] == 2 and books[at]["language"] == "English"
    assert books[at + 1]["slug"] == r["slug"] and books[at + 1]["language"] == "French"
    assert books[at + 1]["origin"]["slug"] == slug
    # translating the translation still ties the new book to the first one
    r2 = client.post(f"/api/books/{r['slug']}/translate", json={"language": "German"}).json()
    assert state.load_state(r2["slug"])["translated_from"] == slug
    books = client.get("/api/books").json()
    at = [b["slug"] for b in books].index(slug)
    assert books[at]["editions"] == 3 and [b["slug"] for b in books[at + 1:at + 3]] == sorted([r["slug"], r2["slug"]],
        key=lambda s: {r["slug"]: "French", r2["slug"]: "German"}[s])


def test_plan_shows_the_book_structure(client):
    import yaml
    slug = client.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    kinds = [x["kind"] for x in client.get(f"/api/books/{slug}/plan").json()["structure"]]
    assert kinds[0] == "title" and "story" in kinds

    data = yaml.safe_load(EXAMPLE.read_text())
    story = data["pages"][:3]
    data["sections"] = [{"kind": "parents_note"}, {"kind": "story", "pages": 3}, {"kind": "coloring"}, {"kind": "maze"}]
    data["pages"] = [{"kind": "parents_note", "text": "Dear parents"}] + [{**p, "kind": "story"} for p in story] + [
        {"kind": "coloring", "chapter": "Color the fox", "text": "Color it", "prompt": "line art fox"},
        {"kind": "maze", "text": "Help the fox home"}]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": yaml.safe_dump(data, allow_unicode=True)})
    s = client.get(f"/api/books/{slug}/plan").json()["structure"]
    assert [(x["kind"], x["pages"]) for x in s] == [("parents_note", 1), ("story", 3), ("coloring", 1), ("maze", 1)]
    assert s[2]["title"] == "Color the fox"


def test_control_and_correction(client, monkeypatch):
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    _wait(client, client.post(f"/api/books/{slug}/jobs/mock").json()["job"])
    assert client.get(f"/api/books/{slug}/control").json() == {"report": None}

    async def ask(prompt, system, schema=None, images=()):
        return {"issues": [{"page": 6, "problem": "A word is misspelled.", "current": "tete",
                            "replace_with": "tête", "fix": "text", "prompt": "Fix the spelling."},
                           {"page": 6, "problem": "The fox holds no lantern.", "fix": "image",
                            "prompt": "Show the lantern."}]} if len(images) and 6 in range(1, 99) and "page-006.png" in prompt else {"issues": []}

    monkeypatch.setattr(author, "ask", ask)
    r = client.post(f"/api/books/{slug}/control/check").json()["report"]
    assert [i["page"] for i in r["issues"]] == [6, 6] and all(i["status"] == "open" for i in r["issues"])
    a, b = r["issues"]
    # one issue on a page can be ignored while the other stays
    client.put(f"/api/books/{slug}/control/{a['id']}", json={"status": "ignored"})
    rep = client.get(f"/api/books/{slug}/control").json()["report"]
    assert [i["status"] for i in rep["issues"]] == ["ignored", "open"]

    seen = []

    async def revise(yaml_text, instruction):
        seen.append(instruction)
        return yaml_text
    monkeypatch.setattr(author, "revise", revise)
    # a text fix that changes nothing is refused and the issue stays open
    import json
    from bookforge import control
    from bookforge.project import Project
    pr = Project(state.book_dir(slug) / "book.yaml")
    rep = control.load(pr)
    text_issue = rep["issues"][0]
    text_issue.update(fix="text", slot=None, book_page=3, status="open")
    control.report_path(pr).write_text(json.dumps(rep))
    c = client.post(f"/api/books/{slug}/control/{text_issue['id']}/apply", json={"prompt": "Fix the spelling."})
    assert c.status_code == 502 and "no change" in c.json()["detail"]
    assert "page 3 of the `pages:` list in book.yaml" in seen[0] and "page 6 of the printed PDF" in seen[0]
    assert client.get(f"/api/books/{slug}/control").json()["report"]["issues"][0]["status"] == "open"

    # a real change is written to book.yaml, the issue is applied and the book is flagged for a rebuild
    async def revise_ok(yaml_text, instruction):
        return yaml_text.replace("title: ", "title: Fixed ", 1)
    monkeypatch.setattr(author, "revise", revise_ok)
    c = client.post(f"/api/books/{slug}/control/{text_issue['id']}/apply", json={"prompt": "Fix the spelling."})
    assert c.status_code == 200 and c.json() == {"yaml": True}
    rep = client.get(f"/api/books/{slug}/control").json()["report"]
    assert rep["issues"][0]["status"] == "applied" and rep["rebuild"] is True
