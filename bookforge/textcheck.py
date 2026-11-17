"""Text control: before any art is paid for, Claude proofreads the manuscript (the words of book.yaml only, no
pictures), lists the real mistakes and writes the fix for each one.

The report lives in textcheck.json beside book.yaml. Nothing changes until the writer presses Apply; a fix whose
exact words are known is made in place, the others are made together by one page-scoped Claude edit."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import threading
import time
from pathlib import Path

import yaml

from . import author, control, proofing
from .spec import Book, plain

_lock = threading.Lock()
BATCH = 8        # pages proofread per call: few enough to read every word
PARALLEL = 3     # calls in flight at once

SYSTEM = """\
You are the proofreader of a children's book manuscript, before it is illustrated and printed. You are given
every page's words as they will be typeset (numbered as in book.yaml), the data of its games and exercises,
and the brief's rules. Find the real mistakes a careful editor would fix before the book goes to print.

Look for:
- every error of spelling, conjugation, agreement, grammar, punctuation and typography in the book's own
  language, following the language checklist given with the manuscript;
- a missing or doubled word, a sentence cut off, a placeholder left in (TODO, [name], lorem ipsum), words in
  another language than the book's;
- a character's name spelled two ways, or a fact that contradicts another page (a number, a color, who did what);
- a game or exercise whose answer is wrong, has two right answers, or cannot be found from the page;
- the brief's learning rule broken (e.g. the learning words are not marked the way the brief says);
- a picture prompt that contradicts the words of its own page (three apples in the text, five in the prompt).

Rules:
- Every language error is a real mistake and is reported, however small. Beyond language, report only what a
  reader, a parent or a teacher would clearly notice. You are not required to find anything; an empty list is a
  good, normal answer. Never give opinions on style or suggest rewrites for taste, never score. When unsure
  whether something is wrong, leave it out. One mistake is one entry; the same mistake on two pages is two.
- Never translate. Quote the words exactly as they are written, accents included.
- `page` is the book.yaml page number from the "page N" marks; use 0 for words outside the pages (title,
  back-cover blurb, dedication, character descriptions).
- `current` is the exact words as written now (a short span, copied character for character so it can be found)
  and `replace_with` what they must say, whenever the fix is a change of wording. Leave both empty when the fix
  needs more than a swap of words.
- `prompt` is the fix, ready to send to the person who edits book.yaml: one instruction naming the page and the
  field (`text`, `chapter`, `prompt`, a game's data such as `fill_in` items) and quoting the exact words.
- `problem` is one plain sentence a parent could understand.
- Lines marked "Already ignored by the writer" were seen and kept on purpose: never report them again, nor the
  same mistake worded differently.
"""

SCHEMA = {
    "type": "object",
    "properties": {"issues": {"type": "array", "items": {
        "type": "object",
        "properties": {"page": {"type": "integer"}, "problem": {"type": "string"},
                       "current": {"type": "string"}, "replace_with": {"type": "string"},
                       "prompt": {"type": "string"}},
        "required": ["page", "problem", "prompt"]}}},
    "required": ["issues"],
}


def report_path(book_yaml: Path) -> Path:
    return book_yaml.parent / "textcheck.json"


def load(book_yaml: Path) -> dict | None:
    f = report_path(book_yaml)
    return json.loads(f.read_text()) if f.exists() else None


def _save(book_yaml: Path, report: dict) -> None:
    report_path(book_yaml).write_text(json.dumps(report, indent=2, ensure_ascii=False))


def digest(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def manuscript_text(book: Book) -> str:
    """Every word the book prints, page by page, named by the field it lives in."""
    out = ["Outside the pages (page 0):", f"  title: {book.title!r}"]
    if book.subtitle:
        out.append(f"  subtitle: {book.subtitle!r}")
    if book.back_cover and book.back_cover.blurb:
        out.append(f"  back_cover.blurb: {plain(book.back_cover.blurb).strip()!r}")
    if book.front_matter and book.front_matter.dedication:
        out.append(f"  front_matter.dedication: {book.front_matter.dedication!r}")
    for c in book.characters:
        out.append(f"  character {c.name}: {c.description}")
    for n, pg in enumerate(book.pages, 1):
        out.append("")
        out.append(control.manuscript(book, n).replace(f"book.yaml page {n}", f"page {n}", 1))
        if pg.prompt:
            out.append(f"  prompt: {pg.prompt}")
    return "\n".join(out)


async def inspect(book_yaml: Path, brief: dict | None = None) -> dict:
    """Proofread the manuscript and write textcheck.json. Mistakes the writer ignored stay ignored."""
    text = book_yaml.read_text()
    book = Book.model_validate(yaml.safe_load(text))
    ignored = [i for i in (load(book_yaml) or {"issues": []})["issues"] if i.get("status") == "ignored"]
    rules = author._brief_text(brief) if brief else ""
    base = (f"The book is written in {book.language}.\n\nLanguage checklist:\n{proofing.rules(book.language)}\n\n"
            + (f"The brief:\n{rules}\n\n" if rules else "") + f"The whole manuscript:\n{manuscript_text(book)}\n")
    if ignored:
        base += "\nAlready ignored by the writer:\n" + "\n".join(
            f"- page {i['page']}: {i['problem']}" + (f" (\"{i['current']}\")" if i.get("current") else "") for i in ignored)
    n = len(book.pages)
    # a few pages per call, each read word by word; the whole book is there for names and facts across pages
    chunks = [list(range(a, min(a + BATCH, n + 1))) for a in range(1, n + 1, BATCH)] or [[]]
    chunks[0] = [0] + chunks[0]
    sem = asyncio.Semaphore(PARALLEL)

    async def one(pages: list[int]) -> list[dict]:
        shown = [p for p in pages if p]
        span = (f"pages {shown[0]} to {shown[-1]}" if len(shown) > 1 else f"page {shown[0]}") if shown else ""
        what = " and ".join(x for x in ("the words outside the pages (page 0)" if 0 in pages else "", span) if x)
        async with sem:
            out = await author.ask(f"{base}\n\nProofread {what} now, every word, against the checklist. Report "
                                   f"mistakes on those pages only.", SYSTEM, SCHEMA)
        return [i for i in out.get("issues", []) if isinstance(i, dict) and _page(i) in pages]

    found = await asyncio.gather(*(one(c) for c in chunks))
    fresh = []
    for i in (x for batch in found for x in batch):
        if not str(i.get("problem", "")).strip():
            continue
        issue = {"page": int(i["page"]), "problem": i["problem"].strip(), "current": (i.get("current") or "").strip(),
                 "replace_with": (i.get("replace_with") or "").strip(), "prompt": (i.get("prompt") or "").strip()}
        if not any(control._same(issue, g) for g in ignored):
            fresh.append(issue)
    issues = sorted(fresh + ignored, key=lambda i: i["page"])
    for k, i in enumerate(issues, 1):
        i["id"] = f"t{k:03d}"
        i.setdefault("status", "open")    # open | applied | ignored
    report = {"checked": time.time(), "yaml": digest(text), "pages": n, "issues": issues}
    with _lock:
        _save(book_yaml, report)
    return report


def _page(i: dict) -> int:
    try:
        return int(i.get("page", -1))
    except (TypeError, ValueError):
        return -1


def view(book_yaml: Path) -> dict | None:
    report = load(book_yaml)
    if report and book_yaml.exists():
        report["stale"] = report.get("yaml") != digest(book_yaml.read_text())
    return report


def set_status(book_yaml: Path, issue_id: str, status: str) -> dict:
    with _lock:
        report = load(book_yaml) or {"issues": []}
        issue = next((i for i in report["issues"] if i["id"] == issue_id), None)
        if not issue:
            raise KeyError(issue_id)
        issue["status"] = status
        _save(book_yaml, report)
        return issue


def _swap(node, word: re.Pattern, new: str):
    """`node` with every match of `word` in its strings replaced, and how many there were."""
    if isinstance(node, str):
        out, k = word.subn(lambda _: new, node)
        return out, k
    if isinstance(node, dict):
        total, res = 0, {}
        for key, v in node.items():
            res[key], k = _swap(v, word, new)
            total += k
        return res, total
    if isinstance(node, list):
        total, res = 0, []
        for v in node:
            x, k = _swap(v, word, new)
            res.append(x)
            total += k
        return res, total
    return node, 0


def direct(data: dict, issue: dict) -> dict | None:
    """Swap the exact words on the issue's own page (or outside the pages for page 0) without asking Claude.
    None when the words are not found there, so Claude makes the fix instead."""
    cur, new = issue.get("current") or "", issue.get("replace_with") or ""
    if not cur.strip() or not new.strip() or cur == new:
        return None
    word = re.compile(rf"(?<!\w){re.escape(cur)}(?!\w)")
    out = dict(data)
    page = issue.get("page") or 0
    if page:
        pages = list(data.get("pages") or [])
        if not 1 <= page <= len(pages):
            return None
        pages[page - 1], k = _swap(pages[page - 1], word, new)
        out["pages"] = pages
    else:
        k = 0
        for key, v in data.items():
            if key not in ("pages", "images", *author.KEPT):
                out[key], c = _swap(v, word, new)
                k += c
    if not k:
        return None
    try:
        Book.model_validate(out)
    except Exception:
        return None
    return out


async def apply(book_yaml: Path, items: list[dict], brief: dict | None = None) -> dict:
    """Make the fixes [{id, prompt}]: exact word swaps in place, the rest in one Claude edit. Returns what changed;
    each issue is marked applied, or keeps its error."""
    report = load(book_yaml) or {"issues": []}
    by_id = {i["id"]: i for i in report["issues"]}
    before = book_yaml.read_text()
    data = yaml.safe_load(before)
    done, ask = [], []
    for it in items:
        issue = by_id.get(it.get("id"))
        if not issue:
            raise KeyError(it.get("id"))
        prompt = (it.get("prompt") or issue["prompt"]).strip()
        edited = prompt != issue["prompt"]    # the writer changed the fix: let Claude read it, no blind swap
        issue["prompt"] = prompt
        if not edited and (fixed := direct(data, issue)) is not None:
            data = fixed
            done.append(issue)
        else:
            ask.append(issue)
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100) if done else before
    error = None
    if ask:
        lines = []
        for i in ask:
            where = f"page {i['page']}" if i["page"] else "outside the pages (title, blurb, dedication, characters)"
            swap = f' Wording: "{i["current"]}" -> "{i["replace_with"]}".' if i.get("current") and i.get("replace_with") else ""
            lines.append(f"- On {where}: {i['prompt']}{swap}")
        try:
            text = await author.revise(text, "Fix these mistakes, each only where it says:\n" + "\n".join(lines), brief=brief)
            done += ask
        except author.AuthorError as e:
            error = str(e)
    with _lock:
        report = load(book_yaml) or {"issues": []}
        for i in report["issues"]:
            if any(d["id"] == i["id"] for d in done):
                i.update(status="applied", prompt=by_id[i["id"]]["prompt"])
                i.pop("error", None)
            elif error and any(a["id"] == i["id"] for a in ask):
                i.update(error=error, prompt=by_id[i["id"]]["prompt"])
        if done:
            book_yaml.write_text(text)
            if report.get("yaml") == digest(before):   # changed only by these fixes: the rest of the list holds
                report["yaml"] = digest(text)
        _save(book_yaml, report)
    return {"applied": [d["id"] for d in done], "error": error, "changed": author.changed_pages(before, text)}
