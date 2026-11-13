"""Control & correction: Claude looks at every built page, lists what is wrong, and for each problem
writes the prompt that fixes it, either a redraw note for the picture or an edit of book.yaml (text, layout).

The report lives in build/control.json. Nothing is changed until the writer presses Apply on an issue."""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path

import yaml

from . import author
from .plan import plan
from .project import Project

BATCH = 5          # pages shown to Claude per call
PARALLEL = 3       # calls in flight at once
FIXES = ("image", "text", "layout")

SYSTEM = """\
You are the proofreader and print controller of a children's book that is about to be published.
You are shown pages of the built PDF as pictures (named page-NNN.png, NNN = the PDF page number), with the
manuscript text each page was made from when it is known. Find the real defects a careful editor would
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
    "text"   - the words in the manuscript must change (spelling, wording);
    "layout" - the words are right but their place, size, alignment or line breaks are wrong.
  When the manuscript text is not known for a page, its words are part of the picture: use "image".
- `prompt` is the fix, ready to send, written as an instruction and nothing else:
    for "image": what the redrawn picture must show or the exact words it must carry, and "keep everything
      else as it is";
    for "text" and "layout": an instruction to the person who edits book.yaml (the page's `text`,
      `text_position`, `layout`, `chapter` fields), naming the page and quoting the exact words.
- `current` and `replace_with` are only for a wording fix: what is written now and what it must say.
- `problem` is one plain sentence a parent could understand. `page` is the PDF page number.
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


def page_info(project: Project) -> dict[int, dict]:
    """For every PDF page: its proof image, the picture it carries (slot id) and the manuscript text when known."""
    m = json.loads(project.manifest.read_text())
    slots = {s.id: s for s in plan(project.book)}
    info: dict[int, dict] = {}
    for n in range(1, m["pages"] + 1):
        pic = next((i["src"] for i in m["images"] if i["page"] == n and _slot_of(i["src"]) in slots), None)
        sid = _slot_of(pic) if pic else None
        text = None
        if sid and (mt := re.fullmatch(r"p(\d+)", sid)):
            pg = project.book.pages[int(mt.group(1)) - 1]
            text = "\n".join(x for x in (pg.chapter, pg.text) if x)
        info[n] = {"proof": project.proofs / f"page-{n:03d}.png", "slot": sid, "text": text,
                   "lettered": bool(sid and slots[sid].lettering)}
    return info


async def _check_batch(project: Project, pages: list[int], info: dict, language: str) -> list[dict]:
    lines = []
    for n in pages:
        t = info[n]["text"]
        lines.append(f"page-{n:03d}.png: " + (f"manuscript text:\n{t}" if t else "text unknown (part of the picture)"))
    prompt = (f"The book is written in {language}. Check these pages.\n\n" + "\n\n".join(lines)
              + "\n\nReturn every real defect on these pages only.")
    out = await author.ask(prompt, SYSTEM, SCHEMA, images=[info[n]["proof"] for n in pages])
    return [i for i in out.get("issues", []) if i.get("page") in pages]


def _normalise(issue: dict, info: dict) -> dict:
    """Route the fix to something the studio can really do on that page."""
    p = info.get(issue["page"], {})
    fix = issue["fix"] if issue.get("fix") in FIXES else "layout"
    if p.get("lettered") or (fix in ("text", "layout") and not p.get("text")):
        fix = "image"            # its words are drawn into the picture: only a redraw changes them
    if fix == "image" and not p.get("slot"):
        fix = "text"             # a typeset page has no picture of its own to redraw
    return {"page": issue["page"], "problem": issue["problem"].strip(), "current": (issue.get("current") or "").strip(),
            "replace_with": (issue.get("replace_with") or "").strip(), "fix": fix,
            "prompt": issue["prompt"].strip(), "slot": p.get("slot") if fix == "image" else None}


async def inspect(project: Project) -> dict:
    """Read every page of the built book and write build/control.json."""
    if not project.manifest.exists() or not any(project.proofs.glob("page-*.png")):
        raise FileNotFoundError("build the book first")
    info = page_info(project)
    nums = sorted(info)
    sem = asyncio.Semaphore(PARALLEL)

    async def one(chunk):
        async with sem:
            return await _check_batch(project, chunk, info, str(project.book.language))

    found = await asyncio.gather(*(one(nums[i:i + BATCH]) for i in range(0, len(nums), BATCH)))
    issues = [_normalise(i, info) for batch in found for i in batch]
    issues.sort(key=lambda i: i["page"])
    for k, i in enumerate(issues, 1):
        i["id"] = f"c{k:03d}"
        i["status"] = "open"        # open | applied | ignored
    report = {"checked": time.time(), "pages": len(nums), "issues": issues}
    report_path(project).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def set_status(project: Project, issue_id: str, status: str, prompt: str | None = None) -> dict:
    report = load(project) or {"issues": []}
    issue = next((i for i in report["issues"] if i["id"] == issue_id), None)
    if not issue:
        raise KeyError(issue_id)
    issue["status"] = status
    if prompt:
        issue["prompt"] = prompt
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


def apply_text(current_yaml: str, prompt: str):
    """The coroutine that rewrites book.yaml for a text or layout fix."""
    return author.revise(current_yaml, prompt)
