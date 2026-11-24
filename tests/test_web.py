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
    from bookforge.web import jobs
    # every test's book is called "a-fox": jobs left in memory by an earlier test must not answer for this one
    with jobs._lock:
        jobs.JOBS.clear()
        jobs.QUEUE.clear()
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
        if j["status"] not in ("running", "queued"):
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
        if j["status"] not in ("running", "queued"):
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

    async def fake(texts, language, source, check, progress=None):
        out = {k: f"[FR] {v}" if "[[" not in v else v for k, v in texts.items()}
        assert not check(texts, out)
        return out
    monkeypatch.setattr(author, "translate", fake)

    async def no_plan(*a):
        raise AssertionError("nothing in this book teaches or tests: no questions, no Claude call")
    monkeypatch.setattr(author, "translation_plan", no_plan)
    assert client.post(f"/api/books/{slug}/translate/plan", json={"language": "French"}).json() == \
        {"language": "French", "questions": [], "auto": []}
    assert client.post(f"/api/books/{slug}/translate/plan", json={"language": "English"}).status_code == 400
    r = client.post(f"/api/books/{slug}/translate", json={"language": "French"}).json()
    # the progress window ends on the new book: every step done, a button to open it
    prog = client.get(f"/api/books/{slug}/translate/progress").json()
    assert prog["step"] == "done" and prog["percent"] == 100 and prog["result"]["slug"] == r["slug"]
    assert [s["id"] for s in prog["steps"]] == ["translate", "make", "done"]  # nothing to play-test in this book
    assert all(s["state"] == "done" for s in prog["steps"]) and all(u["state"] == "done" for u in prog["units"])
    assert prog["result"]["title"].startswith("[FR]")
    new = Path(settings.load().books_dir) / r["slug"]
    book = yaml.safe_load((new / "book.yaml").read_text())
    assert book["language"] == "French" and book["title"].startswith("[FR]")
    # nothing in this book teaches or tests: a plain translation, nothing adapted, nothing to warn about
    assert r["adaptation"] == {"changes": [], "warnings": [], "decisions": []} == state.load_state(r["slug"])["adaptation"]
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

    async def revise(yaml_text, instruction, brief=None):
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
    text_issue.update(fix="text", slot=None, book_page=2, book_pages=[2], status="open")
    control.report_path(pr).write_text(json.dumps(rep))
    def settle():
        for _ in range(300):
            js = client.get(f"/api/books/{slug}/jobs").json()["jobs"]
            if not any(j["status"] in ("running", "queued") for j in js):
                return js
            time.sleep(0.1)
        raise TimeoutError

    # the fix is queued with a rebuild after it; one that changes nothing leaves the issue open, saying why
    c = client.post(f"/api/books/{slug}/control/{text_issue['id']}/apply", json={"prompt": "Fix the spelling."})
    assert c.status_code == 200 and len(c.json()["jobs"]) == 1
    js = settle()
    assert [j["kind"] for j in js][:2] == ["build", "text"] and js[1]["status"] == "failed"
    assert "page 2 of the `pages:` list in book.yaml" in seen[0] and "page 6 of the printed PDF" in seen[0]
    got = client.get(f"/api/books/{slug}/control").json()["report"]["issues"][0]
    assert got["status"] == "open" and "no change" in got["error"] and got["job"] is None

    # a real change is written to book.yaml, the issue is applied and the book is built again
    async def revise_ok(yaml_text, instruction, brief=None):
        return yaml_text.replace("title: ", "title: Fixed ", 1)
    monkeypatch.setattr(author, "revise", revise_ok)
    c = client.post(f"/api/books/{slug}/control/apply", json={"items": [{"id": text_issue["id"], "prompt": "Fix the spelling."}]})
    assert c.status_code == 200
    js = settle()
    # the rebuild ran after the fix (it fails here only because the test book has placeholder art)
    assert js[0]["kind"] == "build" and js[0]["started"] >= js[1]["ended"] and js[1]["status"] == "done"
    rep = client.get(f"/api/books/{slug}/control").json()["report"]
    assert rep["issues"][0]["status"] == "applied" and "error" not in rep["issues"][0]


def test_book_queue_merges_redraws_and_runs_words_beside_pictures(client, monkeypatch):
    """Nothing is refused while something runs: it waits. Redraws waiting merge into one job, word fixes run
    on their own lane beside the pictures, and a build waits for everything before it."""
    import threading

    from bookforge.web import jobs
    gates: dict[str, threading.Event] = {}
    order: list[str] = []

    def fake_run(job):
        order.append(job.kind)
        gates.setdefault(job.id, threading.Event()).wait(5)
        job.status, job.ended = "done", time.time()
        with jobs._lock:
            jobs.QUEUE[(job.user, job.slug)].remove(job)
            jobs._pump((job.user, job.slug))
    monkeypatch.setattr(jobs, "_run", fake_run)
    slug = "queue-test"
    art = jobs.start(slug, "art")
    with pytest.raises(RuntimeError):
        jobs.start(slug, "art")                      # the same drawing twice is refused, nothing else
    a = jobs.start(slug, "regen", slots=["p001"], note="smaller fox", then_build=True)
    b = jobs.start(slug, "margins", slots=["p002"])
    c = jobs.start(slug, "regen", slots=["p001"], note="facing left")
    assert a is b is c and a.status == "queued" and a.slots == ["p001", "p002"]
    assert a.redraw["p001"] == "smaller fox Also: facing left" and a.fit == ["p002"]
    t = jobs.start(slug, "text", texts=[{"issue": "c001", "prompt": "x", "page": 3}])
    q = jobs.QUEUE[(None, slug)]
    assert [j.kind for j in q] == ["art", "regen", "text", "build"]
    assert t.status == "running" and art.status == "running"   # words go ahead beside the pictures
    gates.setdefault(t.id, threading.Event()).set()
    gates.setdefault(art.id, threading.Event()).set()
    for _ in range(50):
        if a.status == "running":
            break
        time.sleep(0.02)
    assert a.status == "running" and q[-1].status == "queued"   # the build waits for the redraw
    gates.setdefault(a.id, threading.Event()).set()
    for _ in range(50):
        if q and q[-1].status == "running":
            break
        time.sleep(0.02)
    gates.setdefault(q[-1].id, threading.Event()).set()
    for _ in range(50):
        if not q:
            break
        time.sleep(0.02)
    assert order == ["art", "text", "regen", "build"] and not q


def test_revise_changes_only_the_pages_claude_names(client, monkeypatch):
    """Claude sends back only what changes; every other page stays word for word, the brief's style reaches it,
    and an edit that changes nothing is refused instead of reported as done."""
    import yaml
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox",
                                           "writing": {"notes": "short rhyming lines"}}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    before = yaml.safe_load(EXAMPLE.read_text())
    seen = []

    async def ask(prompt, system, schema=None, images=()):
        seen.append(prompt)
        pg = dict(before["pages"][1], text="A brand new second page.")
        return f"```yaml\n{yaml.safe_dump({'pages': {2: pg}, 'book': {'type': 'comic'}})}```"
    monkeypatch.setattr(author, "ask", ask)
    r = client.post(f"/api/books/{slug}/claude/revise", json={"instruction": "Rewrite page 2."}).json()
    after = yaml.safe_load(r["yaml"])
    assert after["pages"][1]["text"] == "A brand new second page."
    assert after["pages"][0] == before["pages"][0] and after["pages"][2:] == before["pages"][2:]
    assert after["type"] == before["type"]                       # settings are not Claude's to change
    assert r["changed"]["pages"] == [2] and r["changed"]["fields"] == []
    assert "# page 2" in seen[0] and "short rhyming lines" in seen[0]

    async def nothing(prompt, system, schema=None, images=()):
        return "```yaml\n{}\n```"
    monkeypatch.setattr(author, "ask", nothing)
    r = client.post(f"/api/books/{slug}/claude/revise", json={"instruction": "Rewrite page 2."})
    assert r.status_code == 502 and "no change" in r.json()["detail"]


def test_apply_patch_inserts_and_deletes_by_the_old_numbers():
    data = {"title": "T", "pages": [{"text": "1"}, {"text": "2"}, {"text": "3"}]}
    out = author.apply_patch(data, {"delete": [2], "insert": [{"after": 0, "page": {"text": "0"}},
                                                               {"after": 3, "page": {"text": "4"}}]})
    assert [p["text"] for p in out["pages"]] == ["0", "1", "3", "4"]
    with pytest.raises(ValueError):
        author.apply_patch(data, {"pages": {9: {"text": "x"}}})


def test_text_control_before_the_art(client, monkeypatch):
    import yaml
    slug = client.post("/api/books", json={"type": "picture_book", "idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": EXAMPLE.read_text()})
    assert client.get(f"/api/books/{slug}/textcheck").json() == {"report": None}
    book = yaml.safe_load(EXAMPLE.read_text())
    word = book["pages"][1]["text"].split()[0]

    async def ask(prompt, system, schema=None, images=()):
        assert not images and "page 2" in prompt
        return {"issues": [{"page": 2, "problem": "A word is misspelled.", "current": word, "replace_with": "Zzfixed",
                            "prompt": "Fix the spelling."},
                           {"page": 3, "problem": "Two names for the fox.", "prompt": "Use one name on page 3."},
                           {"page": 99, "problem": "No such page.", "prompt": "x"}]}
    monkeypatch.setattr(author, "ask", ask)
    r = client.post(f"/api/books/{slug}/textcheck/check").json()["report"]
    assert [i["page"] for i in r["issues"]] == [2, 3] and not r["stale"]
    a, b = r["issues"]

    # an exact word swap is made at once, on its own page only, without Claude
    async def no_revise(*a, **k):
        raise AssertionError("Claude was asked")
    monkeypatch.setattr(author, "revise", no_revise)
    out = client.post(f"/api/books/{slug}/textcheck/apply", json={"items": [{"id": a["id"]}]}).json()
    assert out["applied"] == [a["id"]] and out["changed"]["pages"] == [2]
    now = yaml.safe_load(state.read_yaml(slug))
    assert now["pages"][1]["text"].startswith("Zzfixed") and now["pages"][2:] == book["pages"][2:]
    assert not out["report"]["stale"]

    # the rest goes to one Claude edit; a failure stays on the issue
    async def fails(text, instruction, brief=None):
        raise author.AuthorError("Claude made no change to the book.")
    monkeypatch.setattr(author, "revise", fails)
    out = client.post(f"/api/books/{slug}/textcheck/apply", json={"items": [{"id": b["id"]}]}).json()
    assert out["applied"] == [] and "no change" in out["report"]["issues"][1]["error"]

    # ignored stays ignored on the next check
    client.put(f"/api/books/{slug}/textcheck/{b['id']}", json={"status": "ignored"})
    monkeypatch.setattr(author, "ask", ask)
    r = client.post(f"/api/books/{slug}/textcheck/check").json()["report"]
    assert [i["status"] for i in r["issues"] if i["page"] == 3] == ["ignored"]


def test_control_fixes_lettered_words_in_the_manuscript_before_the_redraw(client, monkeypatch):
    """Words lettered into a picture come from book.yaml: when the mistake is there, a redraw alone would letter
    it again. The fix corrects book.yaml first, then the picture is drawn from the new words."""
    import json

    import yaml

    from bookforge import control
    from bookforge.project import Project
    from bookforge.web import jobs
    data = yaml.safe_load(EXAMPLE.read_text())
    data["images"]["text_in_art"] = True
    slug = client.post("/api/books", json={"idea": "a fox"}).json()["slug"]
    client.put(f"/api/books/{slug}/yaml", json={"yaml": yaml.safe_dump(data, allow_unicode=True)})
    assert _wait(client, client.post(f"/api/books/{slug}/jobs/mock").json()["job"])["status"] == "done"
    p = Project(state.book_dir(slug) / "book.yaml", mock=True)
    info = control.page_info(p)
    n = next(k for k, i in info.items() if i["slot"] == "p001")
    assert "Willowmere" in info[n]["lettering"]

    def issue(cur, new, fix="image"):
        return control._normalise({"page": n, "problem": "A word is misspelled.", "current": cur,
                                   "replace_with": new, "fix": fix, "prompt": f"Write {new}."}, info)
    # the manuscript has the wrong word: fixed there first; the picture misspelling a right word: only a redraw
    assert issue("Willowmere", "Willowmoor")["manuscript"] and issue("Willowmere", "Willowmoor", "text")["manuscript"]
    assert not issue("Wilowmere", "Willowmere")["manuscript"]
    assert issue("Willowmere", "Willowmoor")["fix"] == "image"

    rep = {"checked": 0, "pages": len(info), "issues": [{**issue("Willowmere", "Willowmoor"), "id": "c001", "status": "open"}]}
    control.report_path(Project(state.book_dir(slug) / "book.yaml")).write_text(json.dumps(rep))
    drawn = []

    def fake_run(project, only=None, bump=frozenset(), notes=None, drafts=None, log=print, progress=None):
        drawn.append((set(only), control.lettering_of(project, "p001"), notes))
        return {}
    monkeypatch.setattr(jobs.generate, "run", fake_run)
    told = []

    async def revise(yaml_text, instruction, brief=None):  # the word is also on the back cover: Claude edits
        told.append(instruction)
        return yaml_text.replace("woods of Willowmere", "woods of Willowmoor", 1)
    monkeypatch.setattr(author, "revise", revise)
    assert client.post(f"/api/books/{slug}/control/c001/apply", json={}).status_code == 200
    for _ in range(300):
        js = client.get(f"/api/books/{slug}/jobs").json()["jobs"]
        if not any(j["status"] in ("running", "queued") for j in js):
            break
        time.sleep(0.1)
    kinds = {j["kind"]: j for j in js}
    assert kinds["text"]["status"] == "done" and kinds["regen"]["status"] == "done"
    assert "Willowmoor" in yaml.safe_load(state.read_yaml(slug))["pages"][0]["text"]
    assert "page 1 of the `pages:` list" in told[0] and '"Willowmere" -> "Willowmoor"' in told[0]
    # the picture was drawn from the corrected words, with the fix as its note
    assert drawn == [({"p001"}, control.lettering_of(Project(state.book_dir(slug) / "book.yaml"), "p001"),
                      {"p001": "Write Willowmoor."})] and "Willowmoor" in drawn[0][1]
    got = client.get(f"/api/books/{slug}/control").json()["report"]["issues"][0]
    assert got["status"] == "applied" and "error" not in got
