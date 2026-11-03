"""Checks the user's prompts before any money is spent, and says how to fix each problem."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..spec import Book
from .prompting import characters_in

TEXT_WORDS = re.compile(r"\b(says?|saying|written|writing|lettering|text|caption|label(?:led|ed)?|title|"
                        r"logo|sign that|banner reading|spell(?:s|ing)?|word)\b", re.I)
QUOTED = re.compile(r"[\"“][^\"”]{2,}[\"”]")
STYLE_OF = re.compile(r"\b(disney|pixar|dreamworks|ghibli|marvel|dc comics|pokemon|"
                      r"in the style of [A-Z][a-z]+ [A-Z][a-z]+)\b", re.I)
MAX_CHARS_PER_IMAGE = 3
MAX_LETTERED_WORDS, MAX_LETTERED_LINES = 45, 8
NON_LATIN = re.compile(r"[^\u0000-\u024F\u1E00-\u1EFF\u2000-\u206F\u20A0-\u20CF\u2100-\u214F]")


@dataclass
class Issue:
    where: str
    level: str  # "warn" | "error"
    message: str


def lint(book: Book) -> list[Issue]:
    issues: list[Issue] = []

    def check_prompt(where: str, prompt: str, text: str, explicit, lettered: bool = False):
        words = len(prompt.split())
        if words < 6:
            issues.append(Issue(where, "warn", f"prompt is only {words} words - say who, doing what, where, "
                                               "and the mood/lighting for a stronger image"))
        if TEXT_WORDS.search(prompt) or QUOTED.search(prompt):
            issues.append(Issue(where, "warn", "the page text is lettered into the image automatically; keep words "
                                               "out of the prompt itself") if lettered else
                          Issue(where, "warn", "prompt seems to ask for words inside the image; AI lettering "
                                               "comes out garbled - put words in the page text or a comic bubble"))
        if STYLE_OF.search(prompt):
            issues.append(Issue(where, "error", "names a studio/franchise/artist style - risky for KDP and "
                                                "copyright; describe the look instead (e.g. 'soft 3D animation look')"))
        chars = characters_in(book, explicit, prompt)
        if len(chars) > MAX_CHARS_PER_IMAGE:
            issues.append(Issue(where, "warn", f"{len(chars)} recurring characters in one image - consistency "
                                               f"drops past {MAX_CHARS_PER_IMAGE}; consider splitting the scene"))
        in_text = {c.name for c in characters_in(book, None, text)} - {c.name for c in chars}
        if in_text and explicit is None:
            issues.append(Issue(where, "warn", f"page text mentions {', '.join(sorted(in_text))} but the prompt "
                                               "doesn't - add them to the prompt or `characters:` if they should appear"))

    if len(book.style.split()) < 12:
        issues.append(Issue("style", "warn", "style is short - name the medium, line, texture, palette and lighting "
                                             "(it is repeated in every prompt and drives consistency)"))
    if STYLE_OF.search(book.style):
        issues.append(Issue("style", "error", "style names a studio/franchise/artist - describe the look instead"))
    for c in book.characters:
        if len(c.description.split()) < 10:
            issues.append(Issue(f"character {c.name}", "warn",
                                "description is thin - give species/age, build, hair/fur colors, eye color, "
                                "and one or two signature clothing items so every image matches"))

    for i, p in enumerate(book.pages, 1):
        where = f"page {i}"
        if p.prompt:
            check_prompt(where, p.prompt, p.text, p.characters, book.lettered(p))
        if book.lettered(p):
            words, lines = len(p.text.split()), len([l for l in p.text.splitlines() if l.strip()])
            if words > MAX_LETTERED_WORDS or lines > MAX_LETTERED_LINES:
                issues.append(Issue(where, "warn", f"{words} words / {lines} lines to letter into one image - long "
                                                   "lettering gets misspelled more; split the page in two"))
            if NON_LATIN.search(p.text + (p.chapter or "")):
                issues.append(Issue(where, "error", "non-Latin script in lettered text - image models can't letter "
                                                    "it reliably; set text_in_art: false for this page or book"))
        for k, panel in enumerate(p.panels, 1):
            check_prompt(f"{where} panel {k}", panel.prompt, "", panel.characters)  # names in dialogue needn't appear
        if p.layout == "spread" and p.prompt and not re.search(r"\b(left|right|side)\b", p.prompt, re.I):
            issues.append(Issue(where, "warn", "spread: say where the main subject sits (left or right) so it "
                                               "doesn't land in the fold"))
        if book.type == "picture_book" and len(p.text.split()) > 60:
            issues.append(Issue(where, "warn", f"{len(p.text.split())} words is a lot for a picture-book page "
                                               "(aim for under 50); the type will shrink to fit"))
    check_prompt("cover", book.cover_prompt, book.title, None)
    return issues
