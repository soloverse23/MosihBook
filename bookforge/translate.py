"""A finished book in another language (a full translation): the same illustrations, every page kept.

Every image whose prompt is unchanged by the translation is reused as is (no cost). Images with the
book's words drawn into them (text_in_art) change prompt, so they are left out and drawn again.

Games, lessons and [[marked]] learning words often only work in the language they were written in
(a rhyme, a first letter, a grammar rule, an odd one out that hinges on spelling). A full translation
runs a short workflow over those parts:
  1. scan     `context()` finds them, for free, before Claude is asked anything
  2. adapt    Claude translates the book and rewrites the parts that would break, so they teach the same
              thing at the same level in the new language and still fit the same picture
  3. check    `fits()` re-validates the translated book (one answer per game, distinct items), then a
              play-test (author.playtest) solves every game and lesson as a reader of the new language
  4. report   what was adapted is kept with the new book (behind a button); only what Claude could not
              fix is shown as a warning
Books with none of these parts are translated in one pass, exactly as before.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import time
from pathlib import Path

import yaml

from . import spec
from .art.prompting import characters_in
from .plan import plan

# what the translation carries over from build/: the art and what the generator knows about it
BUILD_KEEP = ("art", "thumbs", "review.json", "notes.json", "variations.json")


def pin_characters(data: dict) -> dict:
    """Write out who appears on each page and panel. Without a list, characters are found by name in the
    page text, so translated (or transliterated) names would change the prompts and lose the art."""
    book = spec.Book.model_validate(data)
    out = copy.deepcopy(data)
    for p, raw in zip(book.pages, out["pages"]):
        if p.kind == "maze":  # its art is described by maze.start/goal, which are not translated
            continue
        if p.characters is None:
            raw["characters"] = [c.name for c in characters_in(book, None, p.prompt or "", p.text)]
        for panel, raw_panel in zip(p.panels, raw.get("panels") or []):
            if panel.characters is None:
                words = " ".join(b.text for b in panel.bubbles)
                raw_panel["characters"] = [c.name for c in characters_in(book, None, panel.prompt, words)]
    return out


def texts(data: dict, observation: dict | None = None) -> dict[str, str]:
    """Every string a reader sees, keyed by where it lives. Prompts, style and names stay as they are.
    `observation` (build/observation.json) adds the search-and-find word lists, keyed finds.<slot>.<n>."""
    out: dict[str, str] = {}

    def put(key, value):
        if isinstance(value, str) and value.strip():
            out[key] = value

    for k in ("title", "subtitle", "about_author"):
        put(k, data.get(k))
    for k in ("dedication", "copyright"):
        put(f"front_matter.{k}", (data.get("front_matter") or {}).get(k))
    put("back_cover.blurb", (data.get("back_cover") or {}).get("blurb"))
    for k in ("topic", "explain", "marking"):
        put(f"learning.{k}", (data.get("learning") or {}).get(k))
    for i, p in enumerate(data.get("pages") or []):
        put(f"pages.{i}.text", p.get("text"))
        put(f"pages.{i}.chapter", p.get("chapter"))
        for j, panel in enumerate(p.get("panels") or []):
            for k, b in enumerate(panel.get("bubbles") or []):
                put(f"pages.{i}.panels.{j}.bubbles.{k}.text", b.get("text"))
        for j, pair in enumerate((p.get("matching") or {}).get("pairs") or []):
            for side in (0, 1):
                put(f"pages.{i}.matching.pairs.{j}.{side}", pair[side])
        for j, it in enumerate((p.get("fill_in") or {}).get("items") or []):
            put(f"pages.{i}.fill_in.items.{j}.prompt", it.get("prompt"))
            put(f"pages.{i}.fill_in.items.{j}.answer", it.get("answer"))
        for j, g in enumerate((p.get("odd_one_out") or {}).get("groups") or []):
            for k, item in enumerate(g.get("items") or []):  # the answer follows its item (see apply)
                put(f"pages.{i}.odd_one_out.groups.{j}.items.{k}", item)
        for k in ("title", "name_label", "date_label"):
            put(f"pages.{i}.certificate.{k}", (p.get("certificate") or {}).get(k))
    # the software's own words: the built-in ones follow the new language by themselves, only the
    # book's own overrides need translating
    for k, v in (data.get("words") or {}).items():
        put(f"words.{k}", v)
    for sid, v in (observation or {}).items():
        for n, item in enumerate(v.get("items", [])):
            put(f"finds.{sid}.{n}", item.get("name"))
    return out


def apply(data: dict, translated: dict[str, str]) -> dict:
    out = copy.deepcopy(data)
    for key, value in translated.items():
        if key.startswith("finds."):
            continue
        *path, last = key.split(".")
        node = out
        for part in path:
            node = node[int(part)] if isinstance(node, list) else node.setdefault(part, {})
        node[int(last) if isinstance(node, list) else last] = value
    # an odd-one-out answer is one of its group's items: keep it pointing at the same item, now translated
    for p_old, p_new in zip(data.get("pages") or [], out.get("pages") or []):
        for g_old, g_new in zip((p_old.get("odd_one_out") or {}).get("groups") or [],
                                (p_new.get("odd_one_out") or {}).get("groups") or []):
            norm = [x.strip().lower() for x in g_old["items"]]
            if g_old["answer"].strip().lower() in norm:
                g_new["answer"] = g_new["items"][norm.index(g_old["answer"].strip().lower())]
    return out


def check(original: dict[str, str], translated: dict[str, str]) -> list[str]:
    """What is wrong with a translation: missing pieces or lost [[highlight]] marks."""
    errs = [f"{k}: missing" for k in original if not (translated.get(k) or "").strip()]
    errs += [f"{k}: keep exactly {original[k].count('[[')} [[marked]] passage(s)" for k in original
             if k in translated and translated[k].count("[[") != original[k].count("[[")]
    errs += [f"{k}: unbalanced [[ ]] marks" for k in translated if translated[k].count("[[") != translated[k].count("]]")]
    errs += [f"{k}: keep {ph} exactly as it is" for k in original if k in translated
             for ph in ("{year}", "{author}") if ph in original[k] and ph not in translated[k]]
    return errs


# template sections whose words teach or test something (bookforge/templates.py KINDS)
TEACHING_KINDS = {"parents_note", "theme_intro", "reference", "comprehension", "main_game", "matching", "fill_in",
                  "odd_one_out", "observation", "guided_drawing", "imagination", "final_challenge"}


def context(data: dict) -> dict:
    """Step 1 of a full translation: the parts that may only work in the book's own language.
    {"learning": {...} | None, "pages": [{"where": "pages.<i>", "kind", "picture"}]}; {} when there are none."""
    pages = []
    for i, p in enumerate(data.get("pages") or []):
        kind = p.get("kind")
        if kind in TEACHING_KINDS or "[[" in (p.get("text") or "") or any(p.get(k) for k in spec.DATA_KINDS.values()):
            pages.append({"where": f"pages.{i}", "kind": kind or "story page with marked learning words",
                          "picture": p.get("prompt") or ""})
    learning = {k: v for k, v in (data.get("learning") or {}).items() if k in ("topic", "explain", "marking") and v}
    return {"learning": learning or None, "pages": pages} if learning or pages else {}


def fits(data: dict, translated: dict[str, str]) -> list[str]:
    """What breaks once the translation is in the book: two items that became the same word, an
    odd-one-out answer that is no longer exactly one of its items, anything else the book's rules refuse."""
    from pydantic import ValidationError
    try:
        spec.Book.model_validate(apply(data, translated))
    except ValidationError as e:
        return [f"{'.'.join(map(str, err['loc'])) or 'book'}: {err['msg']}" for err in e.errors()]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return [f"book: {e}"]
    return []


def teaching_view(data: dict, translated: dict[str, str], ctx: dict) -> str:
    """What the play-test reads: the translated lesson and teaching pages, answers and pictures included."""
    book = apply(data, translated)
    fields = ("chapter", "text", *dict.fromkeys(spec.DATA_KINDS.values()))
    pages = []
    for c in ctx.get("pages") or []:
        p = book["pages"][int(c["where"].split(".")[1])]
        pages.append({"where": c["where"], "kind": c["kind"], "picture": c["picture"],
                      **{k: p[k] for k in fields if p.get(k)}})
    lesson = {k: v for k, v in (book.get("learning") or {}).items() if k in ("topic", "explain", "marking")}
    return yaml.safe_dump({"learning": lesson or None, "pages": pages}, sort_keys=False, allow_unicode=True, width=100)


def label(data: dict, where: str) -> str:
    """'pages.3' -> 'Page 4 (Odd one out)': where a change or a problem is, in the user's words."""
    from .templates import KINDS
    parts = (where or "").split(".")
    pages = data.get("pages") or []
    if parts[0] == "pages" and len(parts) > 1 and parts[1].isdigit() and int(parts[1]) < len(pages):
        kind = pages[int(parts[1])].get("kind")
        return f"Page {int(parts[1]) + 1}" + (f" ({KINDS[kind][0]})" if kind in KINDS else "")
    return {"learning": "The lesson", "finds": "Things to find"}.get(parts[0], "The book")


def finds(build: Path) -> dict:
    f = build / "observation.json"
    return json.loads(f.read_text()) if f.exists() else {}


def make(src: Path, dst: Path, data: dict, translated: dict[str, str], language: str) -> dict:
    """Write the translated book to `dst` and carry over every image it can reuse.
    Returns {"reused": [slot ids], "redraw": [slot ids]}."""
    original = pin_characters(data)
    new = apply(original, translated)
    new["language"] = language
    old_slots = {s.id: s.prompt for s in plan(spec.Book.model_validate(original))}
    new_slots = plan(spec.Book.model_validate(new))
    reuse = [s.id for s in new_slots if old_slots.get(s.id) == s.prompt and (src / "build" / "art" / f"{s.id}.png").exists()]
    redraw = [s.id for s in new_slots if s.id not in reuse]

    dst.mkdir(parents=True)
    for item in src.iterdir():  # character sheets, user reference images, attachments
        if item.name in ("build", "book.yaml", "studio.json"):
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, dst / item.name)
    build = dst / "build"
    build.mkdir()
    for name in BUILD_KEEP:
        f = src / "build" / name
        if f.is_dir():
            shutil.copytree(f, build / name)
        elif f.exists():
            shutil.copy2(f, build / name)
    (build / "thumbs" / "front.jpg").unlink(missing_ok=True)
    for sid in redraw:
        for f in (build / "art" / f"{sid}.png", build / "thumbs" / f"{sid}.jpg"):
            f.unlink(missing_ok=True)
    reviews = build / "review.json"
    if reviews.exists():
        r = json.loads(reviews.read_text())
        r["_chosen"] = {k: v for k, v in r.get("_chosen", {}).items() if k in reuse}
        reviews.write_text(json.dumps(r, indent=2))
    obs = {k: {**v, "items": [{**item, "name": translated.get(f"finds.{k}.{n}", item.get("name"))}
                              for n, item in enumerate(v.get("items", []))]}
           for k, v in finds(src / "build").items() if k in reuse}
    if obs:
        (build / "observation.json").write_text(json.dumps(obs, indent=2, ensure_ascii=False))
    spec.Book.model_validate(new)
    (dst / "book.yaml").write_text(yaml.safe_dump(new, sort_keys=False, allow_unicode=True, width=100))
    return {"reused": reuse, "redraw": redraw}


# ---- progress ---------------------------------------------------------------------------------------------
# While Claude writes the translation, its answer is read as it grows: each item it finishes marks a part of
# the book done, so the author sees which page it is on, how far it got and the last line it translated.

_FIELD = re.compile(r'"(id|text|adapted)"\s*:\s*(?:"((?:[^"\\]|\\.)*)"|\[)')


def _unit(key: str) -> str:
    """The part of the book an item belongs to: pages.3.text -> pages.3."""
    parts = key.split(".")
    if parts[0] == "pages" and len(parts) > 1:
        return f"pages.{parts[1]}"
    if parts[0] in ("learning", "finds"):
        return parts[0]
    return "back" if parts[0] in ("back_cover", "about_author") else "front"


def _unit_label(data: dict, unit: str) -> str:
    return {"front": "Title and first pages", "back": "Back cover", "learning": "The lesson",
            "finds": "Things to find"}.get(unit) or label(data, unit)


class Progress:
    """How far a full translation has got. Called as `progress(event, **info)` by author.translate_full;
    `view()` is what the browser polls."""

    # the share of the bar each pass and play-test fills: (translate from, to), play-test to
    FULL = [((4, 66), 80), ((80, 89), 93), ((93, 96), 97)]
    PLAIN = [((4, 90), 90), ((90, 96), 96)]

    def __init__(self, data: dict, texts: dict[str, str], language: str, full: bool):
        self.language, self.full = language, full
        self.ids = list(texts)
        self.unit_of = {k: _unit(k) for k in texts}
        self.units = list(dict.fromkeys(self.unit_of.values()))
        self.labels = {u: _unit_label(data, u) for u in self.units}
        self.started = time.time()
        self.step = "translate"        # translate | playtest | make | done | failed
        self.attempt = 0
        self.passed: set[str] = set()   # items finished in the first pass (the parts already translated)
        self.finished: set[str] = set()  # items finished in this pass
        self.current = ""               # the item being written now
        self.last = ""                  # the last line translated
        self.note = ""
        self.adapting = False
        self.problems = 0
        self.percent, self.cap = 2, 4
        self._seen = 0
        self.error = ""
        self.result: dict | None = None
        self.ended = 0.0
        self.event("translate", attempt=0)

    def _range(self, attempt: int):
        plan_ = self.FULL if self.full else self.PLAIN
        return plan_[min(attempt, len(plan_) - 1)]

    def _bump(self, value: float, cap: float) -> None:
        self.percent = max(self.percent, int(value))
        self.cap = max(self.percent, int(cap))

    def __call__(self, event: str, **info) -> None:
        self.event(event, **info)

    def event(self, event: str, attempt: int = 0, text: str = "", problems: int = 0) -> None:
        (lo, hi), play = self._range(attempt)
        if event == "translate":
            self.step, self.attempt, self.adapting = "translate", attempt, False
            self.finished, self.current, self._seen = set(), "", 0
            if attempt == 0:
                self.note = f"Translating into {self.language}"
            self._bump(lo, lo + (hi - lo) * 0.05)
        elif event == "text":
            self._read(text)
            share = len(self.finished) / max(1, len(self.ids))
            self._bump(lo + (hi - lo) * share, lo + (hi - lo) * min(1.0, share + 1.5 / max(1, len(self.ids))))
            if self.adapting:
                self.note = "Writing down what was adapted for the new language"
            elif self.current:
                verb = "Translating" if attempt == 0 else "Going over"
                self.note = f"{verb} {self.labels[self.unit_of[self.current]]}"
        elif event == "redo":
            self.problems = problems
            self.note = (f"{problems} item{'s' if problems != 1 else ''} came back incomplete: "
                         f"translating again (pass {attempt + 2})")
        elif event == "playtest":
            self.step = "playtest"
            self.note = f"A {self.language}-speaking teacher is playing every game and reading every lesson"
            self._bump(hi, play)
        elif event == "fix":
            self.problems = problems
            self.note = (f"The play-test found {problems} problem{'s' if problems != 1 else ''}: "
                         f"fixing {'them' if problems != 1 else 'it'} (pass {attempt + 2})")
        elif event == "make":
            self.step, self.note = "make", "Copying the pictures and setting up the new book"
            self._bump(97, 99)

    def _read(self, text: str) -> None:
        """Take in the answer so far: only the part after the last field already read."""
        for m in _FIELD.finditer(text, self._seen):
            if m.end() >= len(text):    # a field still being written: read it again with more text
                break
            field, value = m.group(1), m.group(2)
            if field == "adapted":
                self.adapting = True
            elif field == "id" and value in self.unit_of:
                self.current = value
            elif field == "text" and self.current:
                self.finished.add(self.current)
                if self.attempt == 0:
                    self.passed.add(self.current)
                try:
                    self.last = json.loads(f'"{value}"')
                except ValueError:
                    self.last = value
            self._seen = m.end()
        # an item whose text is still being written is the one Claude is on
        if self.current in self.finished and not self.adapting:
            nxt = next((k for k in self.ids[self.ids.index(self.current) + 1:] if k not in self.finished), None)
            self.current = nxt or self.current

    def done(self, slug: str, result: dict) -> None:
        self.step, self.result, self.note, self.ended = "done", {"slug": slug, **result}, "", time.time()
        self.percent = self.cap = 100

    def failed(self, message: str) -> None:
        self.stopped = self.step if self.step != "done" else "make"
        self.step, self.error, self.ended = "failed", message, time.time()

    def view(self) -> dict:
        done_units = {self.unit_of[k] for k in self.passed}
        open_units = {self.unit_of[k] for k in self.ids if k not in self.passed}
        current = self.unit_of.get(self.current) if self.step == "translate" and not self.adapting else None
        units = [{"label": self.labels[u], "short": str(int(u.split(".")[1]) + 1) if u.startswith("pages.")
                  else {"front": "T", "learning": "L", "finds": "F", "back": "B"}[u],
                  "state": "now" if u == current else "done" if u in done_units and u not in open_units else "todo"}
                 for u in self.units]
        if self.step not in ("translate", "failed"):
            units = [{**u, "state": "done"} for u in units]
        order = ["translate", "playtest", "make", "done"] if self.full else ["translate", "make", "done"]
        at = order.index(self.stopped if self.step == "failed" else self.step)
        names = {"translate": "Translate every page", "playtest": f"Play every game in {self.language}",
                 "make": "Make the new book", "done": "Ready"}
        now = "failed" if self.step == "failed" else "now"
        steps = [{"id": s, "label": names[s],
                  "state": "done" if i < at or self.step == "done" else now if i == at else "todo"}
                 for i, s in enumerate(order)]
        return {"language": self.language, "step": self.step, "steps": steps, "percent": self.percent,
                "cap": self.cap, "note": self.note, "units": units,
                "items_done": len(self.passed if self.attempt else self.finished), "items": len(self.ids),
                "pass": self.attempt + 1, "last": self.last[-240:], "elapsed": round((self.ended or time.time()) - self.started),
                "error": self.error, "result": self.result}
