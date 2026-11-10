"""Stages 2-3: character sheets, then the cover (the book's style anchor), then every page.

Each image is generated once and checked by the vision review, which only flags problems.
Nothing is ever redrawn automatically: an image is generated again only when the user asks (Redo).
"""
from __future__ import annotations

import contextvars
import hashlib
import html
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image
from rich.console import Console

from .. import characters, settings as app_settings
from ..cache import JsonStore, request_key
from ..plan import Slot, plan
from ..project import Project
from ..providers.base import get_provider
from ..providers.openai_images import MAX_REFS, ModerationBlocked
from . import prompting
from .review import get_reviewer

console = Console()


char_slot_id = characters.char_id
# a Redo steps the variation counter past every key an older run may have used (up to 3 attempts per image),
# so the redone image is always a fresh one
REDO_STEP = 3


def run(project: Project, only: set[str] | None = None, bump: set[str] = frozenset(),
        notes: dict[str, str] | None = None, pilot: int = 0,
        log: Callable[[str], None] = console.print,
        progress: Callable[[str, str, object], None] | None = None) -> dict:
    """Generate all missing art. `only` limits to slot ids; `bump` forces fresh variations;
    `notes` adds an art-director note to a slot (kept for future runs); `pilot` limits the
    run to characters + cover + the first N illustrations.
    `progress(event, slot_id, info)` gets "total" (info = image count), "phase" (slot_id = group title),
    "start" and "done" (info = the result text) so a UI can show each image as it lands."""
    progress = progress or (lambda *a: None)
    book, settings = project.book, project.book.images
    provider = get_provider(settings)
    reviewer = get_reviewer(settings)
    variations = JsonStore(project.build / "variations.json")
    note_store = JsonStore(project.build / "notes.json")
    reviews = JsonStore(project.build / ("review-mock.json" if project.mock else "review.json"))
    finds = JsonStore(project.build / ("observation-mock.json" if project.mock else "observation.json"))
    for sid in bump:
        variations.data[sid] = variations.data.get(sid, 0) + REDO_STEP
    note_store.data.update(notes or {})
    variations.save()
    note_store.save()

    # the character directory: lock sheets from earlier runs, pull series characters from the library,
    # and prompt with the locked wording so every page repeats it word for word
    characters.adopt(project, log)
    for name in characters.drifted(project):
        log(f"[yellow]{name}: book.yaml describes them differently from the locked character - using the "
            f"locked look. To redraw them: bookforge characters reset book.yaml \"{name}\"[/]")
    for c in book.characters:
        c.description = characters.description(project, c)
    by_name = {char_slot_id(c.name): c for c in book.characters}

    slots = plan(book)
    by_id = {s.id: s for s in slots}
    chars = [s for s in slots if s.kind == "character"]
    covers = [s for s in slots if s.kind in ("cover", "back")]
    pages = [s for s in slots if s.kind not in ("character", "cover", "back")]
    if pilot:
        only = {s.id for s in chars + covers[:1] + pages[:pilot]}
    failures: dict[str, str] = {}
    progress("total", "", sum(1 for s in slots if only is None or s.id in only))

    def refs_for(slot: Slot, previous: Path | None) -> list[prompting.Ref]:
        if slot.kind == "character":
            return [prompting.Ref(project.root / slot.user_reference, prompting.USER_REF_ROLE)] \
                if slot.user_reference else []
        refs = [prompting.Ref(characters.locked(project, c) or project.art_path(char_slot_id(c.name)),
                              prompting.character_role(c) + (" Draw them as black outline line art, no color."
                                                             if slot.kind == "coloring" else ""))
                for c in book.characters if c.name in slot.characters]
        if settings.style_anchor and slot.kind not in ("cover", "coloring"):
            role = prompting.LETTERED_STYLE_ROLE if slot.lettering else prompting.STYLE_ROLE
            refs.append(prompting.Ref(project.art_path("cover-front"), role))
        if previous:
            refs.append(prompting.Ref(previous, "the previous page of the book, for continuity of setting "
                                                "and lighting only."))
        return [r for r in refs if r.path.exists()][:MAX_REFS]

    def make(slot: Slot, previous: Path | None = None) -> str:
        if slot.kind == "character" and slot.id not in bump and (sheet := characters.locked(project, by_name[slot.id])):
            if not project.art_path(slot.id).exists():
                shutil.copyfile(sheet, project.art_path(slot.id))
            return "locked in the character directory (no cost)"
        refs = refs_for(slot, previous)
        size = provider.request_size(slot.aspect)
        quality = settings.quality_for(slot.id)
        # the default quality keeps the old cache keys, so switching it never re-buys existing art
        model_key = provider.model if quality == settings.quality else f"{provider.model}@{quality}"
        base = variations.data.get(slot.id, 0)
        prompt = prompting.with_refs(slot.prompt, refs, note_store.data.get(slot.id))
        keys = [request_key(model_key, prompt, size, [r.path for r in refs], base + n) for n in range(REDO_STEP)]
        chosen = reviews.data.get("_chosen", {}).get(slot.id, {})
        prompt_id = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        # paid art is never redrawn on its own: only a Redo (bump) replaces an existing image
        if not project.mock and slot.id not in bump and project.art_path(slot.id).exists():
            if chosen.get("prompt", prompt_id) != prompt_id:
                failures[slot.id] = "the page changed since this image was drawn - press Redo to redraw it"
            return "already drawn (no cost)"
        # an older run may have kept a later attempt for this exact request: keep using it
        key = chosen["key"] if chosen.get("key") in keys and (project.cache / f"{chosen['key']}.png").exists() \
            else keys[0]
        cached = project.cache / f"{key}.png"
        if not cached.exists():
            try:
                tmp = cached.with_suffix(f".{slot.id}.part")  # atomic: two slots may share one request
                tmp.write_bytes(provider.generate(prompt, size, [r.path for r in refs], quality))
                tmp.replace(cached)
            except ModerationBlocked:
                failures[slot.id] = "blocked by OpenAI moderation - reword the prompt (neutral, visual terms)"
                return "FAILED"
            if not project.mock:
                app_settings.record_spend(settings.cost(slot.id), project.root.name, slot.id)
        if slot.kind == "observation" and finds.data.get(slot.id, {}).get("key") != key:
            # the find-list is read from the finished picture, so everything on it really is there
            finder = reviewer or get_reviewer(settings.model_copy(update={"review": True}))
            finds.data[slot.id] = {"key": key, "items": finder.find_items(cached, book.language)}
            finds.save()
        best = reviews.data.get(key, {}).get("verdict")
        if best is None and reviewer:
            best = reviewer.review(cached, prompt, refs, slot.expected_text)
            reviews.data[key] = {"slot": slot.id, "verdict": best}
        shutil.copyfile(cached, project.art_path(slot.id))
        if slot.kind == "character":
            characters.lock(project, by_name[slot.id], project.art_path(slot.id))
        reviews.data.setdefault("_chosen", {})[slot.id] = {"key": key, "attempts": 1, "prompt": prompt_id}
        # only misspelled or stray lettering is serious enough to flag
        if best and (problems := serious_problems(best, bool(slot.lettering))):
            failures[slot.id] = "use Redo with a note: " + "; ".join(problems)
        return "done"

    def tracked(slot: Slot, previous: Path | None = None) -> str:
        progress("start", slot.id, None)
        try:
            result = make(slot, previous)
        except Exception as e:
            progress("done", slot.id, f"FAILED: {e}")
            raise
        if project.art_path(slot.id).exists():
            make_thumb(project, slot.id)
        progress("done", slot.id, result)
        return result

    def batch(title: str, group: list[Slot]) -> None:
        group = [s for s in group if only is None or s.id in only]
        if not group:
            return
        log(f"[bold]{title}[/] ({len(group)})")
        progress("phase", title, len(group))
        if settings.chain_previous_page and title == "Illustrations":
            prev = None
            for s in group:
                log(f"  {s.id}: {tracked(s, prev)}")
                prev = project.art_path(s.id)
            return
        with ThreadPoolExecutor(settings.max_workers) as pool:
            # each worker runs in this run's context (the signed-in account's keys and spend log)
            futures = {pool.submit(contextvars.copy_context().run, tracked, s): s for s in group}
            for f in as_completed(futures):
                log(f"  {futures[f].id}: {f.result()}")
        reviews.save()

    # order matters: pages reference the character sheets and the cover
    batch("Character sheets", chars)
    batch("Cover (style anchor)", covers)
    batch("Illustrations", pages)
    reviews.save()
    write_review_page(project, [by_id[s] for s in by_id], reviews.data, failures)
    for sid, why in failures.items():
        console.print(f"[yellow]NEEDS ATTENTION[/] {sid}: {why}")
    return failures


def text_problems(verdict: dict, lettered: bool) -> list[str]:
    """The lettering faults of a verdict, worded for the person fixing the page."""
    if not lettered:
        return ["has text"] if verdict.get("has_text") else []
    out = [f"text: {e}" for e in verdict.get("text_errors", [])]
    if not verdict.get("text_legible", True):
        out.append("lettering hard to read")
    if not verdict.get("text_in_safe_area", True):
        out.append("lettering too close to the edge (may be trimmed)")
    return out


def serious_problems(verdict: dict, lettered: bool) -> list[str]:
    """The faults that really ruin a page: misspelled lettering, or writing in art meant to have none.
    Everything else the reviewer says (margins, outfits, style) is only a note."""
    if not lettered:
        return ["has text"] if verdict.get("has_text") else []
    return [f"text: {e}" for e in verdict.get("text_errors", [])]


def review_notes(verdict: dict, lettered: bool) -> list[str]:
    """Everything the reviewer said about an image, shown only when the user asks for it."""
    return text_problems(verdict, lettered) + [i for k in ("character_issues", "anatomy_issues",
                                               "composition_issues", "style_issues") for i in verdict.get(k, [])]


def make_thumb(project: Project, slot_id: str) -> Path:
    """A 720px JPEG of a slot's art for the web UI and review page."""
    thumb = project.build / "thumbs" / f"{slot_id}.jpg"
    thumb.parent.mkdir(exist_ok=True)
    with Image.open(project.art_path(slot_id)) as im:
        im = im.convert("RGB")
        im.thumbnail((720, 720))
        tmp = thumb.with_suffix(".part.jpg")
        im.save(tmp, quality=85)
        tmp.replace(thumb)
    return thumb


def write_review_page(project: Project, slots: list[Slot], reviews: dict, failures: dict[str, str]) -> None:
    """build/review.html: every image with its prompt, review and the command to redo it."""
    chosen = reviews.get("_chosen", {})
    cards = []
    for s in slots:
        art = project.art_path(s.id)
        if not art.exists():
            continue
        make_thumb(project, s.id)
        info = chosen.get(s.id, {})
        verdict = reviews.get(info.get("key", ""), {}).get("verdict") or {}
        issues = serious_problems(verdict, bool(s.lettering)) if verdict else []
        status = "attention" if s.id in failures else "ok"
        cards.append(f"""<article class="card {status}">
<img src="thumbs/{s.id}.jpg" alt="{s.id}" loading="lazy">
<div class="meta"><h3>{s.id} <span>{s.kind}</span></h3>
{'<p class="warn">' + html.escape(failures[s.id]) + '</p>' if s.id in failures else ''}
{'<ul>' + ''.join(f'<li>{html.escape(i)}</li>' for i in issues) + '</ul>' if issues else ''}
<details><summary>Prompt</summary><pre>{html.escape(s.prompt)}</pre></details>
<code>bookforge regen book.yaml {s.id} --note "..."</code></div></article>""")
    (project.build / "review.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Art review</title><style>
:root {{ --bg:#F4F1EC; --card:#FFFFFF; --ink:#2B2622; --muted:#7A716A; --warn:#B4441E; --ok:#3E7C4F; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1C1A18; --card:#282522; --ink:#EEE8E0; --muted:#A39A90; }} }}
body {{ background:var(--bg); color:var(--ink); font:14px/1.5 system-ui,sans-serif; margin:0; padding:24px 16px; }}
h1 {{ font-weight:600; }} .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; }}
.card {{ background:var(--card); border-radius:10px; overflow:hidden; border-top:4px solid var(--ok); }}
.card.attention {{ border-top-color:var(--warn); }} .card img {{ width:100%; display:block; }}
.meta {{ padding:10px 14px 14px; }} h3 {{ margin:0; font-size:15px; }} h3 span {{ color:var(--muted); font-weight:400; }}
.score {{ color:var(--muted); margin:2px 0 6px; }} .warn {{ color:var(--warn); font-weight:600; }}
pre {{ white-space:pre-wrap; font-size:12px; }} code {{ font-size:11px; color:var(--muted); word-break:break-all; }}
</style></head><body><h1>{html.escape(project.book.title)}: art review</h1>
<p>{len(failures)} image(s) need a fix.</p>
<div class="grid">{''.join(cards)}</div></body></html>""")
