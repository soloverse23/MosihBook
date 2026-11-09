"""Checks the user's prompts before any money is spent. Only problems serious enough to ruin a book are
reported: a named studio/artist style (KDP and copyright risk) and lettering in a script the image model
can't write."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..spec import Book

STYLE_OF = re.compile(r"\b(disney|pixar|dreamworks|ghibli|marvel|dc comics|pokemon|"
                      r"in the style of [A-Z][a-z]+ [A-Z][a-z]+)\b", re.I)
NON_LATIN = re.compile(r"[^\u0000-ɏḀ-ỿ -⁯₠-⃏℀-⅏]")


@dataclass
class Issue:
    where: str
    level: str  # "error"
    message: str


def lint(book: Book) -> list[Issue]:
    issues: list[Issue] = []

    def check_prompt(where: str, prompt: str):
        if STYLE_OF.search(prompt):
            issues.append(Issue(where, "error", "names a studio/franchise/artist style - risky for KDP and "
                                                "copyright; describe the look instead (e.g. 'soft 3D animation look')"))

    if STYLE_OF.search(book.style):
        issues.append(Issue("style", "error", "style names a studio/franchise/artist - describe the look instead"))
    for i, p in enumerate(book.pages, 1):
        where = f"page {i}"
        if p.prompt:
            check_prompt(where, p.prompt)
        if book.lettered(p) and NON_LATIN.search(p.text + (p.chapter or "")):
            issues.append(Issue(where, "error", "non-Latin script in lettered text - image models can't letter "
                                                "it reliably; set text_in_art: false for this page or book"))
        for k, panel in enumerate(p.panels, 1):
            check_prompt(f"{where} panel {k}", panel.prompt)
    check_prompt("cover", book.cover_prompt)
    return issues
