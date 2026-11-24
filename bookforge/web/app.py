"""MosiBooks: a local web UI over the BookForge pipeline. Start with `mosibooks serve`."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import author, characters, control, exports, kdp, settings, spec, templates, textcheck
from ..art.lint import lint
from ..art.generate import review_notes, serious_problems
from ..imaging import margins
from ..plan import plan
from ..spec import QUALITY_COST_USD
from ..project import Project
from . import auth, jobs, state, updater

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="MosiBooks")
auth.install(app)


@app.middleware("http")
async def _fresh_static(request, call_next):
    """The app's own pages, scripts and styles are revalidated on every load, so an update or edit shows
    at once instead of a cached older app.js."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/") and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-cache"
    return response


def _dir(slug: str) -> Path:
    try:
        return state.book_dir(slug)
    except KeyError:
        raise HTTPException(404, f"no book {slug!r}")


async def _claude(coro):
    try:
        return await coro
    except author.AuthorError as e:
        raise HTTPException(502, str(e))


# ---- settings -------------------------------------------------------------------------------

@app.get("/api/settings")
def get_settings():
    return {"settings": settings.load().masked(), "trims": sorted(kdp.TRIMS),
            "papers": list(kdp.SPINE_FACTOR), "path": "" if _accounts() else str(settings.PATH), "server": _accounts(), "credit": settings.credit()}


@app.put("/api/settings")
def put_settings(updates: dict = Body(...)):
    try:
        return {"settings": settings.save(updates).masked(), "credit": settings.credit()}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/settings/test/{what}")
async def test_settings(what: str):
    if what == "claude":
        s = settings.load()
        if _accounts() and not s.anthropic_api_key:
            raise HTTPException(400, "Add your Anthropic API key first")
        mode = "API key" if s.anthropic_api_key else "Claude Code login"
        reply = await _claude(author.ping())
        return {"ok": True, "message": f"Claude answered {reply!r} via {mode} ({s.claude_model})"}
    if what == "openai":
        s = settings.load()
        if not s.openai_api_key:
            raise HTTPException(400, "no OpenAI key saved")
        try:
            from openai import OpenAI
            models = {m.id for m in OpenAI(api_key=s.openai_api_key).models.list()}
        except Exception as e:
            raise HTTPException(502, f"OpenAI rejected the key: {e}")
        has = "available" if s.image_model in models else "NOT in this account's model list"
        return {"ok": True, "message": f"key works; {s.image_model} is {has}"}
    raise HTTPException(404)


# ---- first-run setup ------------------------------------------------------------------------

def _claude_bin() -> str | None:
    """The Claude Code CLI: on PATH, or the copy bundled inside claude-agent-sdk."""
    import shutil
    if found := shutil.which("claude"):
        return found
    try:
        import claude_agent_sdk
        bundled = Path(claude_agent_sdk.__file__).parent / "_bundled"
        return next((str(bundled / n) for n in ("claude", "claude.exe") if (bundled / n).exists()), None)
    except ImportError:
        return None


def _claude_status() -> dict:
    import subprocess
    exe = _claude_bin()
    if not exe:
        return {"installed": False, "logged_in": False}
    try:
        out = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True, timeout=15)
        d = json.loads(out.stdout or "{}")
    except Exception:
        d = {}
    return {"installed": True, "logged_in": bool(d.get("loggedIn")), "email": d.get("email"),
            "plan": d.get("subscriptionType"), "method": d.get("authMethod")}


def _accounts() -> bool:
    return auth.mode() == "accounts"


@app.get("/api/setup")
def setup_status():
    s = settings.load()
    server = _accounts()  # each account brings its own keys; the server's Claude login is never shared
    return {"onboarded": s.onboarded or bool(s.openai_api_key),
            "claude": {"installed": False, "logged_in": False} if server else _claude_status(),
            "server": server, "user": settings.current_user.get(),
            "has_anthropic_key": bool(s.anthropic_api_key), "has_openai_key": bool(s.openai_api_key)}


@app.post("/api/setup/claude-login")
def claude_login():
    """Start Claude's browser sign-in on this computer; the page polls /api/setup until it's done."""
    import subprocess
    if _accounts():
        raise HTTPException(400, "On this server, connect Claude with your own Anthropic API key")
    exe = _claude_bin()
    if not exe:
        raise HTTPException(400, "Claude Code isn't available; run: pip install -e '.[web]'")
    subprocess.Popen([exe, "auth", "login", "--claudeai"], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True}


@app.post("/api/setup/done")
def setup_done():
    settings.save({"onboarded": True})
    return {"ok": True}


# ---- self-update (Windows install) ----------------------------------------------------------

@app.get("/api/update")
def update_status(force: bool = False):
    return updater.public(updater.check(force))


@app.post("/api/update/apply")
def update_apply():
    if jobs.busy():
        raise HTTPException(409, "Wait for the pictures or layout that are being made to finish, then update")
    try:
        return {"ok": True, "version": updater.apply()}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Couldn't download the update: {e}")


# ---- books ----------------------------------------------------------------------------------

@app.get("/api/books")
def list_books():
    return state.all_books()


@app.post("/api/books")
def create_book(brief: dict = Body(...)):
    if not (brief.get("idea") or "").strip():
        raise HTTPException(400, "describe the book idea first")
    return {"slug": state.create(brief)}


@app.get("/api/books/{slug}")
def get_book(slug: str):
    _dir(slug)
    text = state.read_yaml(slug)
    job = jobs.running(slug)
    return {**state.summary(slug), "state": state.load_state(slug), "yaml": text, "sources": state.sources(slug),
            "yaml_error": state.validate_yaml(text) if text else None,
            "pages_view": state.pages_view(text),
            "preflight": json.loads(pf.read_text()) if (pf := _dir(slug) / "build" / "preflight.json").exists() else None,
            "files": {n: (_dir(slug) / "build" / n).stat().st_size for n in ("interior.pdf", "cover.pdf")
                      if (_dir(slug) / "build" / n).exists()},
            "exports": exports.ready(_dir(slug) / "build"), "editions": _editions(slug),
            "job": job.id if job else None, "job_kind": job.kind if job else None}


def _editions(slug: str) -> dict:
    """The book this one was translated from, and the translations made of it (or of its original)."""
    origin = state.load_state(slug).get("translated_from")
    root = origin if origin and (state.books_dir() / origin).is_dir() else slug
    out = []
    for d in state.books_dir().iterdir():
        if d.is_dir() and (d / "studio.json").exists() and d.name != root:
            st = state.load_state(d.name)
            if st.get("translated_from") == root:
                b = state.summary(d.name)
                out.append({"slug": d.name, "title": b["title"], "status": b["status"], "language": _language(d.name)})
    origin = state.summary(root) if root != slug else None
    return {"origin": {"slug": root, "title": origin["title"], "status": origin["status"], "language": _language(root)}
            if root != slug else None,
            "translations": sorted(out, key=lambda e: e["language"])}


def _language(slug: str) -> str:
    import yaml
    from ..words import canonical
    brief = (state.load_state(slug).get("brief") or {}).get("language")
    try:
        raw = (yaml.safe_load(state.read_yaml(slug) or "") or {}).get("language") or brief
    except yaml.YAMLError:
        raw = brief
    return canonical(raw) or str(raw)


@app.delete("/api/books/{slug}")
def delete_book(slug: str):
    import shutil
    shutil.rmtree(_dir(slug))
    return {"ok": True}


@app.put("/api/books/{slug}/state")
def put_state(slug: str, updates: dict = Body(...)):
    _dir(slug)
    allowed = {k: v for k, v in updates.items() if k in ("step", "brief", "answers", "outline")}
    pn = (allowed.get("brief") or {}).get("page_numbers")
    if isinstance(pn, bool) and (text := state.read_yaml(slug)):  # the book is written: the toggle applies to it now
        import yaml
        data = yaml.safe_load(text)
        if isinstance(data, dict) and data.get("page_numbers", True) != pn:
            data["page_numbers"] = pn
            state.write_yaml(slug, yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))
    return state.save_state(slug, **allowed)


@app.put("/api/books/{slug}/yaml")
def put_yaml(slug: str, body: dict = Body(...)):
    _dir(slug)
    text = body.get("yaml", "")
    err = state.validate_yaml(text)
    if err and not body.get("save_invalid"):
        raise HTTPException(422, err)
    state.write_yaml(slug, text)
    return {"ok": True, "yaml_error": err, "pages_view": state.pages_view(text)}


@app.post("/api/books/{slug}/sources")
async def add_source(slug: str, name: str, request: Request):
    """Attach a reference file to the brief. The body is the raw file bytes (no multipart dependency)."""
    _dir(slug)
    try:
        return state.add_source(slug, name, await request.body())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/books/{slug}/sources/{name}")
def remove_source(slug: str, name: str):
    _dir(slug)
    state.remove_source(slug, name)
    return {"sources": state.sources(slug)}


# ---- Claude steps ---------------------------------------------------------------------------

@app.post("/api/books/{slug}/claude/questions")
async def claude_questions(slug: str):
    _dir(slug)
    brief = state.load_state(slug).get("brief") or {}
    qs = await _claude(author.questions(brief, refs=state.sources_text(slug), images=state.source_images(slug)))
    return state.save_state(slug, questions=qs, step="questions")


@app.post("/api/books/{slug}/claude/outline")
async def claude_outline(slug: str, body: dict = Body(default={})):
    _dir(slug)
    st = state.load_state(slug)
    answers = body.get("answers", st.get("answers") or {})
    md = await _claude(author.outline(st.get("brief") or {}, st.get("questions") or [], answers,
                                      body.get("feedback", ""), st.get("outline", "") if body.get("feedback") else "",
                                      refs=state.sources_text(slug), images=state.source_images(slug)))
    return state.save_state(slug, answers=answers, outline=md, step="outline")


@app.post("/api/books/{slug}/claude/write")
async def claude_write(slug: str, body: dict = Body(default={})):
    _dir(slug)
    st = state.load_state(slug)
    md = body.get("outline", st.get("outline", ""))
    text = await _claude(author.write_book(st.get("brief") or {}, md, settings.load().image_block(),
                                                  refs=state.sources_text(slug), images=state.source_images(slug)))
    state.write_yaml(slug, text)
    return {**state.save_state(slug, outline=md, step="manuscript"), "yaml": text}


@app.post("/api/books/{slug}/claude/revise")
async def claude_revise(slug: str, body: dict = Body(...)):
    _dir(slug)
    current = body.get("yaml") or state.read_yaml(slug)
    if not current or not body.get("instruction"):
        raise HTTPException(400, "nothing to revise")
    try:
        import yaml
        yaml.safe_load(current)["pages"]
    except Exception:
        raise HTTPException(422, "book.yaml has errors: fix them in the YAML view first")
    brief = state.load_state(slug).get("brief") or {}
    text = await _claude(author.revise(current, body["instruction"], brief=brief))
    state.write_yaml(slug, text)
    return {"yaml": text, "pages_view": state.pages_view(text), "changed": author.changed_pages(current, text)}


# ---- text control: proofreading the manuscript before any art is paid for -------------------

def _manuscript(slug: str) -> Path:
    f = _dir(slug) / "book.yaml"
    if not f.exists():
        raise HTTPException(409, "write the manuscript first")
    return f


@app.get("/api/books/{slug}/textcheck")
def textcheck_report(slug: str):
    return {"report": textcheck.view(_manuscript(slug))}


@app.post("/api/books/{slug}/textcheck/check")
async def textcheck_check(slug: str):
    """Claude proofreads every page's words and lists the real mistakes, each with its fix."""
    f = _manuscript(slug)
    if err := state.validate_yaml(f.read_text()):
        raise HTTPException(422, f"book.yaml has errors, fix them in the Manuscript step first: {err}")
    await _claude(textcheck.inspect(f, state.load_state(slug).get("brief") or {}))
    return {"report": textcheck.view(f)}


@app.put("/api/books/{slug}/textcheck/{issue_id}")
def textcheck_issue(slug: str, issue_id: str, body: dict = Body(...)):
    if body.get("status") not in ("open", "ignored"):
        raise HTTPException(400, "status must be open or ignored")
    try:
        textcheck.set_status(_manuscript(slug), issue_id, body["status"])
    except KeyError:
        raise HTTPException(404)
    return {"ok": True}


@app.post("/api/books/{slug}/textcheck/apply")
async def textcheck_apply(slug: str, body: dict = Body(...)):
    """Make the fixes [{id, prompt}] in book.yaml: exact word swaps at once, the rest in one Claude edit."""
    f = _manuscript(slug)
    items = body.get("items") or []
    if not items:
        raise HTTPException(400, "pick a fix first")
    try:
        out = await textcheck.apply(f, items, state.load_state(slug).get("brief") or {})
    except KeyError as e:
        raise HTTPException(404, f"no problem {e.args[0]!r}: check the text again")
    return {**out, "report": textcheck.view(f)}


def _translation_source(slug: str, body: dict) -> tuple:
    """The finished book to translate and the language asked for: (folder, book data, language)."""
    import yaml
    from ..words import LANGUAGES, canonical
    d = _dir(slug)
    language = canonical((body.get("language") or "").strip()) if (body.get("language") or "").strip() else None
    if not language:
        raise HTTPException(400, f"choose one of: {', '.join(LANGUAGES)}")
    if not (d / "book.yaml").exists() or not any((d / "build" / "art").glob("*.png")):
        raise HTTPException(400, "this book has no finished art yet: illustrate it first")
    try:
        data = yaml.safe_load(state.read_yaml(slug))
        spec_err = state.validate_yaml(state.read_yaml(slug))
    except yaml.YAMLError as e:
        raise HTTPException(422, f"book.yaml is not valid: {e}")
    if spec_err:
        raise HTTPException(422, f"book.yaml is not valid: {spec_err}")
    if language == canonical(data.get("language")):
        raise HTTPException(400, f"the book is already in {language}")
    return d, data, language


@app.post("/api/books/{slug}/translate/plan")
async def translate_plan(slug: str, body: dict = Body(...)):
    """Before a full translation: the learning points that only work in the book's language, as questions for
    the author ({questions: [{id, where, label, issue, question, options}], auto: [{where, label, change}]}).
    A book with nothing that teaches or tests gets no questions, without asking Claude."""
    from .. import translate
    from ..words import canonical
    d, data, language = _translation_source(slug, body)
    ctx = translate.context(data)
    if not ctx:
        return {"language": language, "questions": [], "auto": []}
    plan = await _claude(author.translation_plan(translate.texts(data, translate.finds(d / "build")), language,
                                                 canonical(data.get("language")) or "English", ctx))
    return {"language": language, **{k: [{**x, "label": translate.label(data, x.get("where", ""))} for x in v]
                                     for k, v in plan.items()}}


# the translations running or lately finished, per (account, book): what the progress window polls
_TRANSLATIONS: dict[tuple, object] = {}


def _tr_key(slug: str) -> tuple:
    return settings.current_user.get(), slug


@app.get("/api/books/{slug}/translate/progress")
def translate_progress(slug: str):
    """How far the translation of this book has got: its steps, the page Claude is on, the last line it
    translated and, once done, the new book."""
    p = _TRANSLATIONS.get(_tr_key(slug))
    if not p:
        raise HTTPException(404, "no translation of this book is running")
    return p.view()


@app.post("/api/books/{slug}/translate")
async def translate_book(slug: str, body: dict = Body(...)):
    """A full translation of this finished book, reusing its illustrations. `answers` are the author's answers
    to the plan's questions ([{where, question, answer}]); Claude follows them.
    While it runs, GET .../translate/progress shows how far it got."""
    from .. import translate
    d, data, language = _translation_source(slug, body)
    key = _tr_key(slug)
    running = _TRANSLATIONS.get(key)
    if running and running.step not in ("done", "failed"):
        raise HTTPException(409, f"this book is already being translated into {running.language}")
    words = translate.texts(data, translate.finds(d / "build"))
    ctx = translate.context(data)
    progress = _TRANSLATIONS[key] = translate.Progress(data, words, language, full=bool(ctx))
    try:
        out = await _translate(slug, d, data, language, body, words, ctx, progress)
    except HTTPException as e:
        progress.failed(str(e.detail))
        raise
    except Exception as e:
        progress.failed(f"The translation stopped: {e}")
        raise
    progress.done(out["slug"], {k: out[k] for k in ("reused", "redraw", "adaptation", "redraw_cost_usd")}
                  | {"title": out["title"]})
    return out


async def _translate(slug, d, data, language, body, words, ctx, progress) -> dict:
    from .. import translate
    from ..words import canonical
    decisions = [{"where": a.get("where") or "", "question": str(a.get("question") or ""),
                  "answer": str(a.get("answer") or "")} for a in body.get("answers") or [] if a.get("question")]
    # a full translation: games and lessons are adapted and play-tested in the new language (translate.py)
    full = await _claude(author.translate_full(
        words, language, canonical(data.get("language")) or "English",
        lambda o, t: translate.check(o, t) + translate.fits(data, t), ctx,
        lambda t: translate.teaching_view(data, t, ctx), decisions, progress=progress))
    progress("make")
    translated = full["texts"]
    adaptation = {k: [{"where": translate.label(data, x["where"]), "text": x.get("change") or x.get("problem")}
                      for x in full[src]] for k, src in (("changes", "adapted"), ("warnings", "unresolved"))}
    adaptation["decisions"] = [{**x, "where": translate.label(data, x["where"])} for x in decisions]
    new_slug = state.slugify(f"{slug[:28]}-{language}")
    result = translate.make(d, state.books_dir() / new_slug, data, translated, language)
    st = state.load_state(slug)
    # every edition points at the first book, so translating a translation still lands in the same family
    origin = st.get("translated_from")
    root = origin if origin and (state.books_dir() / origin).is_dir() else slug
    brief = {**(st.get("brief") or {}), "language": language, "title": translated.get("title", data.get("title"))}
    state.save_state(new_slug, step="art", brief=brief, translated_from=root, adaptation=adaptation,
                     **{k: st[k] for k in ("outline",) if k in st})
    return {"slug": new_slug, **result, "adaptation": adaptation, "title": brief["title"],
            "redraw_cost_usd": round(sum(spec.Book.model_validate(data).images.cost(s) for s in result["redraw"]), 2)}


@app.post("/api/books/{slug}/listing")
async def claude_listing(slug: str):
    _dir(slug)
    text = state.read_yaml(slug)
    if not text:
        raise HTTPException(400, "write the manuscript first")
    listing = await _claude(author.listing(text, state.summary(slug)["pages"]))
    return state.save_state(slug, listing=listing)


# ---- pipeline -------------------------------------------------------------------------------

@app.get("/api/books/{slug}/plan")
def book_plan(slug: str):
    d = _dir(slug)
    try:
        p = Project(d / "book.yaml")
    except Exception as e:
        raise HTTPException(422, f"book.yaml is not valid yet: {e}")
    slots = plan(p.book)
    s = p.book.images
    est = sum(s.cost(x.id) for x in slots)
    return {"slots": [{"id": x.id, "kind": x.kind, "aspect": round(x.aspect, 2), "characters": x.characters,
                       "has_art": p.art_path(x.id).exists(), "quality": s.quality_for(x.id),
                       "cost_usd": round(s.cost(x.id), 3)} for x in slots],
            "high_cost_usd": QUALITY_COST_USD["high"], "base_cost_usd": s.est_cost_per_image_usd,
            "model": s.model, "quality": s.quality, "estimate_usd": round(est, 2),
            "lint": [{"where": i.where, "level": i.level, "message": i.message} for i in lint(p.book)],
            "structure": templates.book_structure(p.book)}


@app.get("/api/templates")
def template_library():
    """Book structure templates, plus the section kinds a template can use."""
    return {"templates": [{**t.model_dump(), "pages": t.page_count(), "builtin": templates.is_builtin(t.id),
                           "saved": templates.is_saved(t.id)}
                          for t in templates.all_templates()],
            "kinds": {k: {"label": label, "guide": guide} for k, (label, guide) in templates.KINDS.items()}}


@app.post("/api/templates")
def save_template(body: dict = Body(...)):
    if not (body.get("name") or "").strip():
        raise HTTPException(422, "Give the template a name")
    try:
        t = templates.save(body)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {**t.model_dump(), "pages": t.page_count()}


@app.post("/api/templates/draft")
async def draft_template(body: dict = Body(...)):
    """Claude turns the writer's words into a structure. Nothing is saved until the writer saves it."""
    request = (body.get("prompt") or "").strip()
    if not request:
        raise HTTPException(422, "Say what order you want")
    return await _claude(author.template_draft(request, body.get("current")))


@app.delete("/api/templates/{tid}")
def delete_template(tid: str):
    if not templates.delete(tid):
        raise HTTPException(404, "Only saved templates can be removed (a built-in one is restored instead)")
    return {"ok": True}


@app.get("/api/characters")
def character_library():
    """The shared character library: every character drawn for any book."""
    return {"characters": characters.library()}


@app.get("/api/characters/export.zip")
def export_characters(ids: str | None = None):
    """The library (or the comma-separated `ids`) as one file to send to another studio."""
    data = characters.export_pack(ids.split(",") if ids else None)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="characters.zip"'})


@app.post("/api/characters/import")
async def import_characters(request: Request):
    """Add the characters from an exported .zip. The body is the raw file bytes."""
    try:
        result = characters.import_pack(await request.body())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {**result, **character_library()}


@app.get("/api/characters/{cid}.png")
def library_sheet(cid: str):
    sheet = characters.library_sheet(cid)
    if not sheet:
        raise HTTPException(404)
    return FileResponse(sheet, headers={"Cache-Control": "no-store"})


@app.delete("/api/characters/{cid}")
def delete_library_character(cid: str):
    if not characters.remove_from_library(cid):
        raise HTTPException(404)
    return character_library()


@app.post("/api/characters/{cid}/sheet")
async def upload_library_sheet(cid: str, request: Request):
    """Replace a library character's look with your own image. The body is the raw image bytes."""
    try:
        characters.replace_library_sheet(cid, await request.body())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return character_library()


@app.get("/api/books/{slug}/characters")
def book_characters(slug: str):
    """The book's character directory: which characters have a locked look."""
    d = _dir(slug)
    try:
        p = Project(d / "book.yaml")
    except Exception as e:
        raise HTTPException(422, f"book.yaml is not valid yet: {e}")
    return {"characters": [{**c, "id": characters.char_id(c["name"])} for c in characters.listing(p)],
            "drifted": characters.drifted(p)}


@app.get("/api/books/{slug}/characters/{cid}.png")
def character_sheet(slug: str, cid: str):
    p = Project(_dir(slug) / "book.yaml")
    c = next((c for c in p.book.characters if characters.char_id(c.name) == cid), None)
    sheet = characters.locked(p, c) if c else None
    if not sheet:
        raise HTTPException(404)
    return FileResponse(sheet, headers={"Cache-Control": "no-store"})


@app.put("/api/books/{slug}/high")
def set_high(slug: str, body: dict = Body(...)):
    """Mark slots for high quality (body: {slots: [...], on: bool}). Rewrites images.high_quality in book.yaml."""
    import yaml
    _dir(slug)
    text = state.read_yaml(slug)
    if not text:
        raise HTTPException(400, "write the manuscript first")
    data = yaml.safe_load(text)
    images = data.setdefault("images", {})
    high = [s for s in images.get("high_quality", []) if s not in body.get("slots", [])]
    if body.get("on"):
        high += body.get("slots", [])
    images["high_quality"] = high
    state.write_yaml(slug, yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))
    return book_plan(slug)


@app.post("/api/books/{slug}/jobs/{kind}")
def start_job(slug: str, kind: str, body: dict = Body(default={})):
    """Queue work for the book. It starts at once when nothing is in its way, else it waits its turn."""
    d = _dir(slug)
    if not (d / "book.yaml").exists():
        raise HTTPException(400, "write the manuscript first")
    if kind not in ("mock", "build", "check") and not settings.load().openai_api_key:
        raise HTTPException(400, "add your OpenAI API key in Settings first")
    if kind == "text":
        raise HTTPException(400, "word fixes are made from Control & correction")
    try:
        job = jobs.start(slug, kind, slots=body.get("slots"), note=body.get("note"),
                         pilot_pages=int(body.get("pages", 3)), force=bool(body.get("force")),
                         then_build=bool(body.get("then_build")))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    if kind in ("pilot", "art"):
        state.save_state(slug, step="art")
    return {"job": job.id}


@app.get("/api/books/{slug}/jobs")
def book_jobs(slug: str):
    """What is running and waiting for the book, in order, and what finished lately."""
    _dir(slug)
    return {"jobs": jobs.book_jobs(slug)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, since: int = 0):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404)
    return job.view(since)


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    """Take a job that is still waiting out of the queue (one that runs cannot be stopped halfway)."""
    if not jobs.cancel(job_id):
        raise HTTPException(409, "only a job that is still waiting can be removed")
    return {"ok": True}


@app.get("/api/books/{slug}/control")
def control_report(slug: str):
    """The last control & correction report of the built book (null before the first check)."""
    d = _dir(slug)
    try:
        report = control.view(Project(d / "book.yaml"))
    except Exception as e:
        raise HTTPException(422, f"book.yaml is not valid: {e}")
    if report:   # the fixes waiting or being made
        busy = jobs.issue_jobs(slug)
        for i in report["issues"]:
            i["job"] = busy.get(i["id"])
    return {"report": report}


@app.post("/api/books/{slug}/control/check")
async def control_check(slug: str):
    """Claude reads every built page and lists the defects, each with the prompt that fixes it."""
    d = _dir(slug)
    p = Project(d / "book.yaml")
    try:
        await _claude(control.inspect(p))
    except FileNotFoundError as e:
        raise HTTPException(409, str(e))
    return {"report": control.view(p)}


@app.put("/api/books/{slug}/control/{issue_id}")
def control_issue(slug: str, issue_id: str, body: dict = Body(...)):
    if body.get("status") not in ("open", "ignored"):
        raise HTTPException(400, "status must be open or ignored")
    try:
        control.set_status(Project(_dir(slug) / "book.yaml"), issue_id, body["status"])
    except KeyError:
        raise HTTPException(404)
    return {"ok": True}


def _checking(slug: str) -> bool:
    return any(j["kind"] == "check" and j["status"] in jobs.ACTIVE for j in jobs.book_jobs(slug))


def _queue_fixes(slug: str, items: list[dict]) -> list[str]:
    """Queue the fixes of a control report: the pictures in one redraw job (drawn at the same time), the words
    in one job beside it (made one after another), then one rebuild of the book."""
    d = _dir(slug)
    p = Project(d / "book.yaml")
    if _checking(slug):
        raise HTTPException(409, "the pages are being read again - wait for the new list of problems")
    report = control.load(p) or {"issues": []}
    by_id = {i["id"]: i for i in report["issues"]}
    redraw, notes, fit, texts, rebuild = {}, {}, {}, [], False
    for it in items:
        issue = by_id.get(it.get("id"))
        if not issue:
            raise HTTPException(404, f"no problem {it.get('id')!r}: check the book again")
        prompt = (it.get("prompt") or issue["prompt"]).strip()
        if not prompt:
            raise HTTPException(400, "write the fix first")
        # lettered words that are wrong in book.yaml itself: a redraw would letter the same mistake again, so
        # the words are fixed there first and the picture is drawn from them after (one job leads to the other)
        wrong_words = issue["fix"] == "image" and issue.get("slot") and (
            issue.get("manuscript") or control.wrong_in_manuscript(issue, control.lettering_of(p, issue["slot"])))
        # a redraw asked only to keep things inside the margin keeps the picture and fits it there instead
        fix = "margin" if issue["fix"] == "image" and margins.is_margin_request(prompt) and not issue.get("replace_with") \
            else issue["fix"]
        control.set_status(p, issue["id"], "open", prompt, error="")
        if prompt == issue["prompt"] and control.is_table_layout(p, issue):
            # a cut word in a table: the layout sizes the columns itself, so the rebuild below is the fix
            control.set_status(p, issue["id"], "applied", prompt, error="")
            rebuild = True
        elif wrong_words:
            texts.append({"issue": issue["id"], "prompt": prompt, "page": issue["page"], "redraw": issue["slot"]})
        elif fix == "margin":
            fit[issue["id"]] = issue["slot"]
        elif fix == "image":
            redraw[issue["id"]] = issue["slot"]
            notes[issue["slot"]] = jobs._join(notes.get(issue["slot"]), prompt)
        else:
            texts.append({"issue": issue["id"], "prompt": prompt, "page": issue["page"]})
    if (redraw or fit or any(t.get("redraw") for t in texts)) and not settings.load().openai_api_key:
        raise HTTPException(400, "add your OpenAI API key in Settings first")
    out = []
    try:
        if redraw:
            out.append(jobs.start(slug, "regen", slots=list(dict.fromkeys(redraw.values())), notes=notes,
                                  issues=redraw).id)
        if fit:
            out.append(jobs.start(slug, "margins", slots=list(dict.fromkeys(fit.values())), issues=fit).id)
        if texts:
            out.append(jobs.start(slug, "text", texts=texts).id)
        if out or rebuild:
            jobs.ensure_build(slug)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    return list(dict.fromkeys(out))


@app.post("/api/books/{slug}/control/{issue_id}/apply")
def control_apply(slug: str, issue_id: str, body: dict = Body(default={})):
    """Queue the fix. A picture is redrawn with the prompt as its note; a text or layout fix rewrites
    book.yaml with Claude. Either way the book is built again afterwards to show it."""
    return {"jobs": _queue_fixes(slug, [{"id": issue_id, "prompt": body.get("prompt")}])}


@app.post("/api/books/{slug}/control/apply")
def control_apply_many(slug: str, body: dict = Body(...)):
    """Queue several fixes at once: [{id, prompt}]."""
    return {"jobs": _queue_fixes(slug, body.get("items") or [])}


@app.delete("/api/books/{slug}/control/{issue_id}/queue")
def control_unqueue(slug: str, issue_id: str):
    """Take a fix that has not started out of the queue."""
    if not jobs.drop_issue(slug, issue_id):
        raise HTTPException(409, "this fix has already started")
    return {"ok": True}


@app.get("/api/books/{slug}/proofs")
def book_proofs(slug: str):
    proofs = _dir(slug) / "build" / "proofs"
    return {"pages": sorted(p.name for p in proofs.glob("page-*.png")) if proofs.is_dir() else [],
            "cover": (proofs / "cover.png").exists()}


@app.get("/api/books/{slug}/front.jpg")
def front_cover(slug: str):
    """The front panel of the cover proof (the wraparound minus back and spine), for library thumbnails."""
    build = _dir(slug) / "build"
    proof, geo, out = build / "proofs" / "cover.png", build / "cover.json", build / "thumbs" / "front.jpg"
    if not proof.exists() or not geo.exists():
        raise HTTPException(404)
    if not out.exists() or out.stat().st_mtime < proof.stat().st_mtime:
        from PIL import Image
        c = json.loads(geo.read_text())
        width_in = c["size_in"][0]
        front_in = (width_in - c["spine_in"]) / 2  # trim + one bleed
        with Image.open(proof) as im:
            x = round(im.width * (1 - front_in / width_in))
            front = im.convert("RGB").crop((x, 0, im.width, im.height))
            front.thumbnail((640, 640))
            out.parent.mkdir(exist_ok=True)
            front.save(out, quality=86)
    return FileResponse(out, headers={"Cache-Control": "no-store"})


@app.get("/api/books/{slug}/review")
def book_review(slug: str):
    """Per-image review results of the most recent art run (real or mock), in book order."""
    d = _dir(slug)
    files = [f for f in (d / "build" / "review.json", d / "build" / "review-mock.json") if f.exists()]
    if not files:
        return {"mock": None, "slots": []}
    latest = max(files, key=lambda f: f.stat().st_mtime)
    reviews = json.loads(latest.read_text())
    try:
        p = Project(d / "book.yaml")
    except Exception as e:
        raise HTTPException(422, f"book.yaml is not valid: {e}")
    chosen, out = reviews.get("_chosen", {}), []
    for s in plan(p.book):
        info = chosen.get(s.id)
        if not info or not (d / "build" / "thumbs" / f"{s.id}.jpg").exists():
            continue
        v = reviews.get(info["key"], {}).get("verdict")
        # issues: only misspelled or stray lettering; notes: everything else, shown on request
        issues = serious_problems(v, bool(s.lettering)) if v else []
        notes = [n for n in review_notes(v, bool(s.lettering)) if n not in issues] if v else []
        out.append({"id": s.id, "kind": s.kind, "thumb": f"thumbs/{s.id}.jpg", "issues": issues, "notes": notes,
                    "ok": not issues})
    return {"mock": latest.name == "review-mock.json", "slots": out}


# ---- files ----------------------------------------------------------------------------------

@app.get("/api/books/{slug}/build/{path:path}")
def build_file(slug: str, path: str):
    root = (_dir(slug) / "build").resolve()
    f = (root / path).resolve()
    if not f.is_relative_to(root) or not f.is_file() or "cache" in f.relative_to(root).parts:
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "no-store"})


def _listing_md(listing: dict) -> str:
    return "\n".join([
        "# KDP listing draft", "", "## Description", listing.get("description", ""), "",
        "## Keywords", *[f"{i}. {k}" for i, k in enumerate(listing.get("keywords", []), 1)], "",
        "## Categories", *[f"- {c}" for c in listing.get("categories", [])], "",
        f"## Reading age\n{listing.get('reading_age', '')}", "",
        f"## AI disclosure\n{listing.get('ai_disclosure', '')}", ""])


@app.get("/api/books/{slug}/export/{name}")
def export_file(slug: str, name: str):
    """Reading and sharing copies of the print files: trimmed, no padding pages, screen size."""
    if name not in exports.KINDS:
        raise HTTPException(404)
    try:
        f = exports.get(_dir(slug) / "build", name)
    except FileNotFoundError as e:
        raise HTTPException(409, f"{e.args[0]} is not built yet")
    return FileResponse(f, filename=f"{slug}-{name}", headers={"Cache-Control": "no-store"})


@app.get("/api/books/{slug}/download.zip")
def download(slug: str):
    d = _dir(slug)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("interior.pdf", "cover.pdf", "preflight.json", "preview.html"):
            if (d / "build" / name).exists():
                z.write(d / "build" / name, name)
        if (d / "book.yaml").exists():
            z.write(d / "book.yaml", "book.yaml")
        listing = state.load_state(slug).get("listing")
        if listing:
            z.writestr("kdp-listing.md", _listing_md(listing))
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'})


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
