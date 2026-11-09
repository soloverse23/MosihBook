"""Book structure templates: an ordered list of sections a book follows (parents' note, story, games...).

    ~/.bookforge/templates/<id>.yaml    one saved template (follows BOOKFORGE_HOME)

Built-in templates ship in the package (bookforge/template_presets/*.yaml) and are shown until the writer saves
their own copy under the same id. A brief picks a template and may change it for that book only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator

from . import settings

BUILTIN = Path(__file__).resolve().parent / "template_presets"

# section kind -> (label, short guidance for Claude)
KINDS: dict[str, tuple[str, str]] = {
    "parents_note": ("Note to parents", "Warm note to parents: the learning goal, what the child learns and why, how it is "
                     "woven into the story, how to read together, which activities follow. Adapted to this book's topic."),
    "story": ("Story", "The illustrated story: one distinct scene per page, a clear beginning, problem, climax and happy "
              "ending. Target words marked with the book's marking rule."),
    "comprehension": ("Comprehension questions", "Exactly 10 numbered questions on ONE page (characters, events, cause and "
                      "effect, problem and solution, simple reasoning, a last personal or imaginative one). Answered "
                      "orally: no answers anywhere in the book."),
    "theme_intro": ("Discover the topic", "Introduces the learning topic in very simple words a child can read alone, with "
                    "short definitions and examples from the story."),
    "reference": ("Learning reference", "Reference pages for the topic only (tables, word lists, worked examples, step by "
                  "step), always adapted to this book's topic: never conjugation tables in a maths book."),
    "main_game": ("Main game", "One complete exercise tied to the story and the topic, with room to write."),
    "coloring": ("Coloring page", "Black-and-white line-art scene from the story (not a repeat of a story picture) with a "
                 "one-line instruction, ideally using the topic (e.g. color the big castle red and the small one blue)."),
    "matching": ("Matching game", "Match related items (word and opposite, sum and answer, number and quantity) by drawing "
                 "lines. Unambiguous: exactly one correct pairing."),
    "fill_in": ("Complete the answer", "Short sentences, sums or challenges where the child writes or picks the answer."),
    "odd_one_out": ("Odd one out", "Several groups of words or numbers; the child finds the one that does not belong. "
                    "Each group has exactly one clear answer, given in words (never depending on picture details)."),
    "maze": ("Maze", "A maze drawn by the book software (always solvable). Write only a short instruction naming who must "
             "reach what, e.g. 'Help Nina reach her school!'. The picture shows the start character and the goal."),
    "observation": ("Observation", "A rich scene to search. Write only the title and instruction; the list of things to "
                    "find is made from the finished picture, so do not write one."),
    "guided_drawing": ("Guided drawing", "Ask the child to draw something from the story that uses the topic; big blank "
                       "space, clear instruction."),
    "imagination": ("Imagination", "The child invents a scene, character or object and describes it with the topic's "
                    "words; big blank space."),
    "final_challenge": ("Final challenge", "A fun last challenge using everything learned, plus a small certificate with "
                        "lines for the child's first name and the date."),
    "solutions": ("Solutions", "Compact answers to every game with objectively checkable answers (not the comprehension "
                  "questions, not drawing pages)."),
    "collection": ("In the same collection", "Only books named in the brief, with their topics; published vs coming soon "
                   "only as stated. Never invent titles, status or dates. End with an invitation to keep learning."),
    "copyright": ("Publishing details", "Collection, full title, author, copyright notice and year, edition. Never invent an "
                  "ISBN, publisher, illustrator or legal text."),
    "custom": ("Custom section", "Follow the section's note."),
}

class Section(BaseModel):
    kind: str
    pages: int = 1
    title: Optional[str] = None
    note: Optional[str] = None
    enabled: bool = True

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in KINDS:
            raise ValueError(f"unknown section kind {v!r}; use one of {', '.join(KINDS)}")
        return v

    @field_validator("pages")
    @classmethod
    def _pages(cls, v: int) -> int:
        if not 0 <= v <= 60:
            raise ValueError("pages must be between 0 and 60")
        return v


class Template(BaseModel):
    id: str
    name: str
    description: str = ""
    audience: Optional[str] = None
    language: Optional[str] = None
    trim: Optional[str] = None
    back_cover: Optional[str] = None  # what the back cover must say (summary, goal, age, activities...)
    sections: list[Section]

    def active(self) -> list[Section]:
        return [s for s in self.sections if s.enabled and s.pages > 0]

    def page_count(self) -> int:
        return sum(s.pages for s in self.active())


def library_dir() -> Path:
    return settings.home() / "templates"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "template"


def _read(f: Path) -> Template | None:
    try:
        return Template.model_validate({"id": f.stem, **(yaml.safe_load(f.read_text()) or {})})
    except Exception:
        return None


def _account_key() -> str | None:
    """With accounts, saved templates live in the key-value store (they survive Vercel restarts)."""
    u = settings.current_user.get()
    return f"templates:{settings.user_id(u)}" if u else None


def _saved() -> dict[str, dict]:
    if key := _account_key():
        from . import kv
        return kv.get(key) or {}
    d = library_dir()
    return {f.stem: yaml.safe_load(f.read_text()) or {} for f in sorted(d.glob("*.yaml"))} if d.exists() else {}


def is_saved(tid: str) -> bool:
    return tid in _saved()


def all_templates() -> list[Template]:
    found: dict[str, Template] = {}
    for f in sorted(BUILTIN.glob("*.yaml")):
        if t := _read(f):
            found[t.id] = t
    for tid, data in _saved().items():  # saved ones override built-ins with the same id
        try:
            found[tid] = Template.model_validate({**data, "id": tid})
        except Exception:
            pass
    return list(found.values())


def get(tid: str) -> Template | None:
    return next((t for t in all_templates() if t.id == tid), None)


def save(data: dict) -> Template:
    t = Template.model_validate({**data, "id": data.get("id") or slugify(data.get("name", ""))})
    body = t.model_dump(exclude={"id"}, exclude_none=True)
    if key := _account_key():
        from . import kv
        kv.set(key, {**_saved(), t.id: body})
        return t
    library_dir().mkdir(parents=True, exist_ok=True)
    (library_dir() / f"{t.id}.yaml").write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100))
    return t


def delete(tid: str) -> bool:
    """Remove a saved template. A built-in comes back (unedited) once its saved copy is gone."""
    if key := _account_key():
        from . import kv
        saved = _saved()
        if saved.pop(tid, None) is None:
            return False
        kv.set(key, saved)
        return True
    f = library_dir() / f"{slugify(tid)}.yaml"
    if f.exists():
        f.unlink()
        return True
    return False


def is_builtin(tid: str) -> bool:
    return (BUILTIN / f"{tid}.yaml").exists()


def structure_text(sections: list[dict | Section], back_cover: str | None = None) -> str:
    """The structure as instructions for Claude: numbered sections with page ranges and guidance."""
    secs = [s if isinstance(s, Section) else Section.model_validate(s) for s in sections]
    secs = [s for s in secs if s.enabled and s.pages > 0]
    lines, n = [], 1
    for s in secs:
        label, guide = KINDS[s.kind]
        rng = f"page {n}" if s.pages == 1 else f"pages {n}-{n + s.pages - 1}"
        lines.append(f"- {rng} ({s.pages}) kind: {s.kind} - {s.title or label}. {guide}"
                     + (f" Writer's note: {s.note}" if s.note else ""))
        n += s.pages
    if back_cover:
        lines.append(f"- back cover must include: {back_cover}")
    return f"Interior pages: {n - 1}.\n" + "\n".join(lines)


def book_structure(book) -> list[dict]:
    """The book's interior as runs of consecutive pages of one kind, in reading order, for the app's flow view.

    A template book's pages carry their section kind. A free book gets its built-in front matter, the story,
    and its closing pages. Each item: kind, title, pages (manuscript pages), and a phase only where the kind
    alone doesn't say where it sits (a copyright page opens a free book but closes a template one)."""
    from .plan import split_chapter
    if not book.structured:
        out = [{"kind": "title", "title": "Title page", "pages": 1},
               {"kind": "copyright", "title": "Copyright", "pages": 1, "phase": "intro"}]
        if book.front_matter.dedication:
            out.append({"kind": "dedication", "title": "Dedication", "pages": 1})
        out.append({"kind": "story", "title": KINDS["story"][0], "pages": len(book.pages)})
        if book.type != "storybook" or (book.images.text_in_art and book.characters):
            out.append({"kind": "the_end", "title": "The End", "pages": 1})
        if book.about_author:
            out.append({"kind": "about", "title": "About the author", "pages": 1})
        return out
    out: list[dict] = []
    for p in book.pages:
        kind = p.kind if p.kind in KINDS else "story"
        if out and out[-1]["kind"] == kind:
            out[-1]["pages"] += 1
            continue
        title = split_chapter(p.chapter)[1] if p.chapter and kind != "story" else ""
        out.append({"kind": kind, "title": title or KINDS[kind][0], "pages": 1})
    return out
