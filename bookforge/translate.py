"""A finished book in another language: the same illustrations, only the words change.

Every image whose prompt is unchanged by the translation is reused as is (no cost). Images with the
book's words drawn into them (text_in_art) change prompt, so they are left out and drawn again.
"""
from __future__ import annotations

import copy
import json
import shutil
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
            g_new["answer"] = g_new["items"][norm.index(g_old["answer"].strip().lower())]
    return out


def check(original: dict[str, str], translated: dict[str, str]) -> list[str]:
    """What is wrong with a translation: missing pieces or lost [[highlight]] marks."""
    errs = [f"{k}: missing" for k in original if not (translated.get(k) or "").strip()]
    errs += [f"{k}: keep exactly {original[k].count('[[')} [[marked]] passage(s)" for k in original
             if k in translated and translated[k].count("[[") != original[k].count("[[")]
    errs += [f"{k}: unbalanced [[ ]] marks" for k in translated if translated[k].count("[[") != translated[k].count("]]")]
    return errs


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
