"""Control & correction: Claude looks at every built page, lists what is wrong, and for each problem
writes the prompt that fixes it, either a redraw note for the picture or an edit of book.yaml (text, layout).

The report lives in build/control.json. Nothing is changed until the writer presses Apply on an issue."""
from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from pathlib import Path

import yaml

from . import author
from .plan import plan
from .project import Project
from .spec import Book, plain

BATCH = 5          # pages shown to Claude per call
PARALLEL = 3       # calls in flight at once
FIXES = ("image", "margin", "text", "layout")
_lock = threading.Lock()   # fixes running side by side each update the one report file

SYSTEM = """\
You are the proofreader and print controller of a children's book that is about to be published.
You are shown pages of the built PDF as pictures (named page-NNN.png, NNN = the PDF page number), with the
manuscript each page was made from when it is known: the page of book.yaml it comes from, its words, and for
game and exercise pages the data the software typesets them from (fill_in items and their answers, matching
pairs, odd_one_out groups). The solutions page prints the answers from the data of the game pages it names. Find the real defects a careful editor would
fix before printing, and for each one say how to fix it.

Look for:
- spelling, accents and typography in the book's own language (e.g. French: tête not téte, reconnaître,
  curly apostrophes ’, the superscript in 1er, 3 dots not 4, a non-breaking space so a number stays with its word);
- words cut off, too close to the page edge, covered by a character or a drawing, or hard to read;
- a line breaking badly (a number or dash alone at the end of a line), text in uneven alignment or size;
- the picture contradicting the words (an object, a number, a mood, a character that is not where the text says);
- a game or exercise whose picture cannot give the answer, or an answer that is wrong;
- printer notes left on a page (e.g. "back cover"), a wrong title, a character drawn in two different looks.

Rules:
- Report only real defects: something a reader, a parent or the printer would clearly notice and be
  bothered by. You are not required to find anything: a clean page has no entry, and an empty list for the
  whole book is a good, normal answer. When unsure that something is a defect, leave it out. Never nitpick,
  never invent a problem to look useful, do not score, give no opinions on style, list no small
  preferences. One real defect is one entry: do not split it into several.
- Never translate. Quote the text exactly as it is written, accents included.
- `fix` says what repairs it:
    "image"  - the picture itself must be redrawn (wrong content, or words that are part of the picture);
    "margin" - words or a face drawn into the picture are right but come too close to the page edge (within
               about 1 cm of the edge, where the printer trims): the picture is drawn again from its current
               version with the same content, laid out inside the safe margin. Use it whenever the only problem
               is closeness to the edge;
    "text"   - the words in the manuscript must change (spelling, wording);
    "layout" - the words are right but their place, size, alignment or line breaks are wrong.
  When the manuscript text is not known for a page, its words are part of the picture: use "image" (or
  "margin" when they are only too close to the edge).
- `prompt` is the fix, ready to send, written as an instruction and nothing else:
    for "image": what the redrawn picture must show or the exact words it must carry, and "keep everything
      else as it is";
    for "text" and "layout": an instruction to the person who edits book.yaml, naming the book.yaml page and
      the field that holds the words (`text`, `chapter`, `text_position`, `layout`, or a game's data such as
      `fill_in` items, `matching` pairs, `odd_one_out` groups) and quoting the exact words. A wrong answer on
      the solutions page is fixed in the game page whose data it comes from.
  Words that are typeset (listed in the manuscript) are always "text" or "layout", never "image", even when
  the page also carries a picture: a redraw would not change them.
- `current` and `replace_with` are only for a wording fix: what is written now and what it must say.
- `problem` is one plain sentence a parent could understand. `page` is the PDF page number.
- Some pages list "Already ignored by the writer". The writer has seen those and decided to keep them as
  they are: never report them again, nor the same defect worded differently.
"""

SCHEMA = {
    "type": "object",
    "properties": {"issues": {"type": "array", "items": {
        "type": "object",
        "properties": {"page": {"type": "integer"}, "problem": {"type": "string"},
                       "current": {"type": "string"}, "replace_with": {"type": "string"},
                       "fix": {"type": "string", "enum": list(FIXES)}, "prompt": {"type": "string"}},
        "required": ["page", "problem", "fix", "prompt"]}}},
    "required": ["issues"],
}


def report_path(project: Project) -> Path:
    return project.build / "control.json"


def load(project: Project) -> dict | None:
    f = report_path(project)
    return json.loads(f.read_text()) if f.exists() else None


def _slot_of(src: str) -> str:
    return Path(src).stem


def _game_lines(pg) -> list[str]:
    """The typeset words of a game page, as they are written in its data."""
    if pg.fill_in:
        return [f"  fill_in item {k}: {it.prompt!r} (answer: {it.answer!r})" for k, it in enumerate(pg.fill_in.items, 1)]
    if pg.matching:
        return [f"  matching pair {k}: {a!r} - {b!r}" for k, (a, b) in enumerate(pg.matching.pairs, 1)]
    if pg.odd_one_out:
        return [f"  odd_one_out group {k}: {g.items} (answer: {g.answer!r})" for k, g in enumerate(pg.odd_one_out.groups, 1)]
    if pg.certificate:
        c = pg.certificate
        return [f"  certificate {k}: {v!r}" for k, v in (("title", c.title), ("name_label", c.name_label),
                                                          ("date_label", c.date_label)) if v]
    return []


def manuscript(book: Book, n: int) -> str:
    """What page n of book.yaml prints, named by its fields so a fix can say where the words live."""
    pg = book.pages[n - 1]
    out = [f"book.yaml page {n}" + (f" (kind: {pg.kind})" if pg.kind else "") + ":"]
    if pg.chapter:
        out.append(f"  chapter: {pg.chapter!r}")
    if pg.text.strip():
        out.append("  text: " + plain(pg.text).strip())
    out += _game_lines(pg)
    if pg.kind == "solutions":  # its answers are printed from the games' own data
        for k, g in enumerate(book.pages, 1):
            if g.drawn_activity and g.kind != "final_challenge":
                out.append(f"  answers from book.yaml page {k} ({g.chapter or g.kind}):")
                out += ["  " + x for x in _game_lines(g)]
    return "\n".join(out)


def page_info(project: Project) -> dict[int, dict]:
    """For every PDF page: its proof image, the picture it carries (slot id), the book.yaml pages it shows and
    their manuscript when known."""
    m = json.loads(project.manifest.read_text())
    book = project.book
    slots = {s.id: s for s in plan(book)}
    marks = m.get("book_pages")  # absent in books built before the layout recorded it
    info: dict[int, dict] = {}
    for n in range(1, m["pages"] + 1):
        pics = [_slot_of(i["src"]) for i in m["images"] if i["page"] == n and _slot_of(i["src"]) in slots]
        if marks is not None:
            pages = [b for b in marks.get(str(n), []) if 1 <= b <= len(book.pages)]
        else:
            pages = [int(mt.group(1)) for sid in pics[:1] if (mt := re.fullmatch(r"p(\d+)", sid))]
        # the page's own picture first; a shared frame or a maze end only when it has none
        own = [sid for sid in pics if any(sid.startswith(f"p{b:03d}") for b in pages)]
        sid = (own or pics or [None])[0]
        text = "\n\n".join(manuscript(book, b) for b in pages) or None
        info[n] = {"proof": project.proofs / f"page-{n:03d}.png", "slot": sid, "text": text,
                   "book_page": pages[0] if len(pages) == 1 else None, "book_pages": pages,
                   "lettered": bool(sid and slots[sid].lettering)}
    return info


def _same(a: dict, b: dict) -> bool:
    """Does a freshly found issue describe a problem the writer already ignored? Same page and either the
    same wording to fix or mostly the same words in the description."""
    if a["page"] != b["page"]:
        return False
    cur_a, cur_b = (a.get("current") or "").strip(), (b.get("current") or "").strip()
    if cur_a and cur_a == cur_b:
        return True
    wa, wb = set(re.findall(r"\w+", a["problem"].lower())), set(re.findall(r"\w+", b["problem"].lower()))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6


async def _check_batch(project: Project, pages: list[int], info: dict, language: str,
                       ignored: list[dict] = ()) -> list[dict]:
    lines = []
    for n in pages:
        t = info[n]["text"]
        lines.append(f"page-{n:03d}.png: " + (f"manuscript:\n{t}" if t else "text unknown (part of the picture)"))
        for i in ignored:
            if i["page"] == n:
                lines.append(f"  Already ignored by the writer: {i['problem']}"
                             + (f" (\"{i['current']}\")" if i.get("current") else ""))
    prompt = (f"The book is written in {language}. Check these pages.\n\n" + "\n\n".join(lines)
              + "\n\nReturn every real defect on these pages only.")
    out = await author.ask(prompt, SYSTEM, SCHEMA, images=[info[n]["proof"] for n in pages])
    return [i for i in out.get("issues", []) if i.get("page") in pages]


def _normalise(issue: dict, info: dict) -> dict:
    """Route the fix to something the studio can really do on that page."""
    p = info.get(issue["page"], {})
    fix = issue["fix"] if issue.get("fix") in FIXES else "layout"
    if fix != "margin" and (p.get("lettered") or (fix in ("text", "layout") and not p.get("text"))):
        fix = "image"            # its words are drawn into the picture: only a redraw changes them
    if fix == "margin" and not p.get("lettered"):
        fix = "layout"           # typeset words: the layout keeps them inside the margin, not the picture
    if fix == "image" and not p.get("slot"):
        fix = "text"             # a typeset page has no picture of its own to redraw
    return {"page": issue["page"], "problem": issue["problem"].strip(), "current": (issue.get("current") or "").strip(),
            "replace_with": (issue.get("replace_with") or "").strip(), "fix": fix,
            "prompt": issue["prompt"].strip(), "slot": p.get("slot") if fix in ("image", "margin") else None,
            "book_page": p.get("book_page"), "book_pages": p.get("book_pages") or []}


async def inspect(project: Project, progress=None) -> dict:
    """Read every page of the built book and write build/control.json. `progress(done, total)` is called as
    each group of pages has been read."""
    if not project.manifest.exists() or not any(project.proofs.glob("page-*.png")):
        raise FileNotFoundError("build the book first")
    info = page_info(project)
    nums = sorted(info)
    sem = asyncio.Semaphore(PARALLEL)
    # what the writer already ignored stays ignored: it is kept in the report and never raised again
    ignored = [i for i in (load(project) or {"issues": []})["issues"] if i.get("status") == "ignored"]

    chunks = [nums[i:i + BATCH] for i in range(0, len(nums), BATCH)]
    read = 0

    async def one(chunk):
        nonlocal read
        async with sem:
            out = await _check_batch(project, chunk, info, str(project.book.language), ignored)
        read += 1
        if progress:
            progress(read, len(chunks))
        return out

    if progress:
        progress(0, len(chunks))
    found = await asyncio.gather(*(one(c) for c in chunks))
    fresh = [_normalise(i, info) for batch in found for i in batch]
    fresh = [i for i in fresh if not any(_same(i, g) for g in ignored)]
    issues = sorted(fresh + ignored, key=lambda i: i["page"])
    for k, i in enumerate(issues, 1):
        i["id"] = f"c{k:03d}"
        i.setdefault("status", "open")        # open | applied | ignored
    report = {"checked": time.time(), "pages": len(nums), "issues": issues}
    with _lock:
        report_path(project).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def set_status(project: Project, issue_id: str, status: str, prompt: str | None = None,
               error: str | None = None) -> dict:
    """Change one issue. `error` says why its fix could not be made ("" clears it)."""
    with _lock:
        report = load(project) or {"issues": []}
        issue = next((i for i in report["issues"] if i["id"] == issue_id), None)
        if not issue:
            raise KeyError(issue_id)
        issue["status"] = status
        if prompt:
            issue["prompt"] = prompt
        if error is not None:
            if error:
                issue["error"] = error
            else:
                issue.pop("error", None)
        report_path(project).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        return issue


def view(project: Project) -> dict | None:
    """The saved report, each image fix with its redraw cost and whether the book was rebuilt since."""
    report = load(project)
    if not report:
        return None
    for i in report["issues"]:
        if i["slot"]:
            i["cost_usd"] = round(project.book.images.cost(i["slot"]), 3)
    built = project.manifest.stat().st_mtime if project.manifest.exists() else 0
    report["rebuild"] = any(i["status"] == "applied" for i in report["issues"]) and \
        report_path(project).stat().st_mtime > built
    return report


def instruction(issue: dict, prompt: str) -> str:
    """What the editor of book.yaml is told. PDF page numbers differ from the pages of book.yaml (cover, front
    matter), so the page is named by its place in book.yaml and its words are quoted."""
    bps = issue.get("book_pages") or ([issue["book_page"]] if issue.get("book_page") else [])
    if len(bps) == 1:
        where = f"On page {bps[0]} of the `pages:` list in book.yaml (page {issue['page']} of the printed PDF)"
    elif bps:
        where = (f"On page {issue['page']} of the printed PDF, which shows pages {', '.join(map(str, bps))} of the "
                 "`pages:` list in book.yaml")
    else:
        where = f"On page {issue['page']} of the printed PDF (find it by its words)"
    quote = f' Wording to change: "{issue["current"]}" -> "{issue["replace_with"]}".' if issue.get("current") and issue.get("replace_with") else ""
    return (f"{where}: {prompt}{quote} The words may live in the page's `text`, `chapter` or in a game's data "
            "(`fill_in` items and answers, `matching` pairs, `odd_one_out` groups; the solutions page prints the "
            "answers from the game pages' data, so fix those there). Change only what this asks.")


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _direct(current_yaml: str, issue: dict) -> str | None:
    """A wording fix whose words appear in book.yaml only inside the pages that print them (for the solutions
    page: also the games its answers come from) is made by replacing them there: no rewrite of the whole
    file, nothing else can move."""
    cur, new = issue.get("current") or "", issue.get("replace_with") or ""
    targets = issue.get("book_pages") or []
    if not cur.strip() or not new.strip() or cur == new or issue["fix"] != "text" or not targets:
        return None
    word = re.compile(rf"(?<!\w){re.escape(cur)}(?!\w)")
    try:
        before = yaml.safe_load(current_yaml)
        pages = before.get("pages") or []
        if any(not 1 <= b <= len(pages) for b in targets):
            return None
        allowed = set(targets)
        if any((pages[b - 1] or {}).get("kind") == "solutions" for b in targets):
            allowed |= {k for k, pg in enumerate(pages, 1) if spec_field(pg)}
        inside = sum(len(word.findall(x)) for b in allowed for x in _strings(pages[b - 1]))
        if not inside or len(word.findall(current_yaml)) != inside:
            return None  # the words are missing, or also elsewhere in the book: let Claude find the right place
        out = word.sub(lambda _: new, current_yaml)
        after = yaml.safe_load(out)
        Book.model_validate(after)
    except Exception:
        return None
    return out if after != before else None


def spec_field(pg) -> bool:
    """Does this book.yaml page hold game data the solutions page prints?"""
    return isinstance(pg, dict) and any(pg.get(f) for f in ("fill_in", "matching", "odd_one_out", "maze"))


async def apply_text(current_yaml: str, issue: dict, prompt: str) -> str:
    """Rewrite book.yaml for a text or layout fix. Raises if nothing changed, so a fix is never
    reported as done when the book is the same."""
    if prompt == issue.get("prompt") and (out := _direct(current_yaml, issue)):
        return out
    new = await author.revise(current_yaml, instruction(issue, prompt))
    if yaml.safe_load(new) == yaml.safe_load(current_yaml):
        raise author.AuthorError("Claude made no change to the book, so nothing was fixed. Edit the fix and try again.")
    return new
