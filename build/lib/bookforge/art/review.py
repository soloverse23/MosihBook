"""Automatic art review: a vision model checks every illustration before it goes in the book.

Each image is compared with the character references and the art direction. Failures come
back with a concrete correction that is fed into the next generation attempt.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

from .prompting import Ref

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["score", "has_text", "text_errors", "text_legible", "text_in_safe_area", "character_issues",
                 "anatomy_issues", "composition_issues", "style_issues", "fix"],
    "properties": {
        "score": {"type": "integer", "description": "1-10 overall fitness for a professionally printed book"},
        "has_text": {"type": "boolean", "description": "any visible letters, numbers, words or watermark"},
        "text_errors": {"type": "array", "items": {"type": "string"},
                        "description": "lettered images only: every difference from the EXPECTED TEXT, one per "
                                       "item, quoting the word (misspelled, missing, extra, garbled, wrong order, "
                                       "missing punctuation); empty when it matches exactly or nothing was expected"},
        "text_legible": {"type": "boolean", "description": "the lettering is crisp and easy for a child to read; "
                                                           "true when no text was expected"},
        "text_in_safe_area": {"type": "boolean", "description": "every letter sits at least ~6% inside each image "
                                                                "edge; true when no text was expected"},
        "character_issues": {"type": "array", "items": {"type": "string"}},
        "anatomy_issues": {"type": "array", "items": {"type": "string"}},
        "composition_issues": {"type": "array", "items": {"type": "string"}},
        "style_issues": {"type": "array", "items": {"type": "string"}},
        "fix": {"type": "string", "description": "one or two imperative sentences to fix the problems, "
                                                 "phrased as instructions to an illustrator; empty if none"},
    },
}

INSTRUCTIONS = """You are the art director of a children's/illustrated book publisher, reviewing one AI
illustration before it is printed. The LAST attached image is the illustration under review; any images
before it are references, described in the brief. Be strict about: visible text of any kind; characters
not matching their references (species, colors, markings, clothing, proportions, age); duplicated or
missing characters; anatomy errors (hands, paws, eyes, limbs); ignoring the composition rules (calm text
areas, subjects away from the fold/edges); style drift from the style reference. Do not penalize
artistic interpretation that fits the brief. Score 9-10 = print-ready, 7-8 = good with minor flaws,
<=6 = must be redone."""

LETTERED = """This illustration is MEANT to carry lettering: the EXPECTED TEXT below. Do not count that text
as a fault. Read every word in the image and compare it with the expected text word by word and punctuation
mark by punctuation mark: list each misspelled, missing, extra, doubled, garbled or out-of-order word in
text_errors, quoting it. Any OTHER text (signs, labels, signatures) is also a text error. Check the lettering
matches the lettering style of the style reference (when one is attached), is legible, and stays inside the
edges. In `fix`, give the exact correction first (e.g. "Spell 'wiggles' with two g's; drop the extra 'the'")."""


def _data_url(path: Path, max_side: int = 1024) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def passed(verdict: dict, min_score: int, lettered: bool = False) -> bool:
    if lettered:
        text_ok = (not verdict.get("text_errors") and verdict.get("text_legible", True)
                   and verdict.get("text_in_safe_area", True))
    else:
        text_ok = not verdict["has_text"]
    return (text_ok and not verdict["character_issues"] and not verdict["anatomy_issues"]
            and verdict["score"] >= min_score)


FIND_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["name", "count"],
        "properties": {"name": {"type": "string"}, "count": {"type": "integer"}}}}},
}

FIND_INSTRUCTIONS = """You prepare a search-and-find game for children aged 6-9 from the attached picture. List 6-8
things a child can find in it: clearly visible, unambiguous objects or animals, each with its exact count in
the picture (only choose things you can count with certainty; prefer counts from 1 to 6). Use short, simple
names in {language}, singular when count is 1 (e.g. "papillon"), plural otherwise."""


def find_list(items: list[dict]) -> list[str]:
    return [f"{i['count']} {i['name']}" for i in items if i.get("count", 0) > 0]


class OpenAIReviewer:
    def __init__(self, model: str):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model

    def review(self, image: Path, prompt: str, refs: list[Ref], expected_text: str = "") -> dict:
        brief = "BRIEF (the prompt the illustrator was given):\n" + prompt
        if expected_text:
            brief = f"{LETTERED}\n\nEXPECTED TEXT (exact):\n<<<\n{expected_text}\n>>>\n\n{brief}"
        if refs:
            brief += "\n\nREFERENCE IMAGES (in order): " + "; ".join(f"{i}: {r.role}" for i, r in enumerate(refs, 1))
        content = [{"type": "input_text", "text": brief}]
        content += [{"type": "input_image", "image_url": _data_url(r.path, 640)} for r in refs]
        content.append({"type": "input_image", "image_url": _data_url(image)})
        resp = self.client.responses.create(
            model=self.model,
            instructions=INSTRUCTIONS,
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_schema", "name": "art_review", "schema": SCHEMA, "strict": True}},
        )
        return json.loads(resp.output_text)

    def find_items(self, image: Path, language: str = "the book's language") -> list[dict]:
        resp = self.client.responses.create(
            model=self.model,
            instructions=FIND_INSTRUCTIONS.format(language=language),
            input=[{"role": "user", "content": [{"type": "input_image", "image_url": _data_url(image)}]}],
            text={"format": {"type": "json_schema", "name": "find_list", "schema": FIND_SCHEMA, "strict": True}},
        )
        return json.loads(resp.output_text)["items"]


class MockReviewer:
    def find_items(self, image: Path, language: str = "") -> list[dict]:
        return [{"name": "stars", "count": 3}, {"name": "cat", "count": 1}, {"name": "flowers", "count": 5}]

    def review(self, image: Path, prompt: str, refs: list[Ref], expected_text: str = "") -> dict:
        return {"score": 9, "has_text": bool(expected_text), "text_errors": [], "text_legible": True,
                "text_in_safe_area": True, "character_issues": [], "anatomy_issues": [],
                "composition_issues": [], "style_issues": [], "fix": ""}


def get_reviewer(settings):
    if settings.provider == "mock":
        return MockReviewer()
    return OpenAIReviewer(settings.review_model) if settings.review else None
