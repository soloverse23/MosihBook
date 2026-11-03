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
