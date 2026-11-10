"""Turns the user's short prompts into fully art-directed prompts.

Every illustration is described in the same labeled structure - references, style, scene,
characters, composition, constraints - with the same style block and character descriptions
repeated verbatim, plus a composition rule derived from its print layout so the art leaves
room for real typesetting. With `text_in_art`, a TEXT block instead asks the model to letter
the page's exact words into the illustration, in the book's one lettering style.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..spec import Book, Character

CONSTRAINTS = [
    "Absolutely no text of any kind: no letters, words, numbers, captions, speech bubbles, signs with "
    "writing, signatures, logos or watermarks. Any sign, book or label must be blank or illegible.",
    "One single coherent illustration - not a collage, not split panels, no borders or frames.",
    "Each named character appears exactly once unless the scene says otherwise.",
    "Correct anatomy: natural hands and paws with the right number of fingers/toes, clear symmetrical eyes.",
]

COMPOSITION = {
    "full_bleed": "Full-page illustration that bleeds off every edge (it will be printed edge to edge). "
                  "Keep faces and key subjects at least 8% away from all edges, because the edges get trimmed.",
    "split": "Illustration for the upper portion of a picture-book page, wider than tall. Center the "
             "subject; the bottom edge meets the text area, so keep the bottom 10% simple.",
    "spread": "Wide panoramic double-page spread. The exact vertical center line is the book's fold: "
              "keep faces and key subjects clearly to the left or right of center, never on it.",
    "spot": "Vignette spot illustration: the subject isolated on a plain warm-white paper background "
            "with soft, fading edges, no frame, no background scenery beyond a hint of ground.",
    "opener": "Full-page children's storybook illustration that bleeds off every edge; the page's words "
              "are printed on top of it. Rich and atmospheric; keep key subjects away from the edges, which "
              "get trimmed.",
    "panel": "A single comic-book panel with cinematic framing and clear staging, readable at small size.",
    "cover": "Front cover artwork for a printed book. One strong, simple, eye-catching focal point that "
             "reads at thumbnail size. Keep the top 30% calm and uncluttered for the title and the "
             "bottom 12% calm for the author name.",
    "back": "Back-cover artwork: quiet, low-detail and atmospheric so text can sit on top of it.",
    "frame": "Decorative page frame for the text pages of the book: small motifs from the story's world "
             "around the edges only. The large center, about 76% of the width and 80% of the height, is "
             "completely empty plain warm paper with nothing in it, because text is printed there: no "
             "character, cloud, leaf or object reaches into it; anything large stays in the corners.",
    "coloring": "A coloring-book page for children to color in: clean black outlines only, on pure white. "
                "Large, simple, closed shapes a child can fill with crayons; whole characters, nothing cropped; "
                "no tiny details, no hatching.",
    "observation": "A rich, busy, full-page search-and-find scene with many clearly separate, countable objects, "
                   "animals and characters spread across the whole picture, each one easy to recognise. Keep the "
                   "bottom third a little calmer: a list is printed there.",
    "maze_end": "Small vignette illustration, the subject isolated on plain pure-white paper with soft fading "
                "edges, no frame, no background scenery.",
    "character": "Character design reference sheet: exactly one full-body view of the character, standing, "
                 "front three-quarter view, neutral friendly expression, even flat lighting, centered, "
                 "plain pure-white background, no shadow, no other objects or characters.",
}

COLORING_STYLE = ("Black-and-white line art for a children's coloring book: thick, clean, even black outlines; pure "
                  "white everywhere inside and around the shapes; no color, no gray, no shading, no texture, no "
                  "filled black areas. Same character designs as the rest of the book, drawn as outlines.")

# lettered slots: the words are part of the picture, so the "no text" rule becomes "only this text"
LETTERED_CONSTRAINT = ("No text anywhere except the words of the TEXT TO LETTER block: no other words, letters, "
                       "numbers, signs with writing, signatures, logos or watermarks.")

LETTERED_COMPOSITION = {
    "full_bleed": "Full-page picture-book illustration that bleeds off every edge, with the page's words lettered "
                  "into it.",
    "opener": "Full-page children's storybook illustration that bleeds off every edge, with the page's words "
              "lettered into it.",
    "spread": "Wide panoramic double-page spread with the words lettered into it. The exact vertical center "
              "line is the book's fold: keep faces, key subjects and every letter clearly to the left or "
              "right of center, never on it.",
    "split": "Full-page illustration: the scene fills roughly the upper 60% and dissolves softly into plain "
             "warm paper below, where the words are lettered.",
    "spot": "Full page of plain warm-white paper with a vignette illustration (soft fading edges, no frame) "
            "and the words lettered around it.",
}

DEFAULT_LETTERING = ("clean, rounded, friendly hand-lettered serif in warm dark ink, generous letter and line "
                     "spacing, large enough for a young child to read")

PLACEMENT = {
    "top": "in the upper part of the image",
    "bottom": "in the lower part of the image",
    "auto": "where the scene has the most calm, open space",
}


@dataclass
class Lettering:
    """Words the image model draws into a picture."""
    text: str                     # exact, line breaks kept
    heading: str | None = None    # chapter title or book title, lettered larger
    placement: str = "auto"       # key into PLACEMENT, or a free description
    note: str = ""                # extra layout direction (author line, barcode gap...)
    highlights: tuple[str, ...] = ()  # words or phrases lettered in the book's highlight style
    highlight_rule: str = ""          # the writer's marking rule (how highlighted words look)


def lettering_block(book: Book, l: Lettering) -> str:
    words = []
    if l.heading:
        words += ["Heading (larger, display lettering):", "<<<", l.heading.strip(), ">>>"]
    if l.text.strip():
        words += ["Body:" if l.heading else "", "<<<", l.text.strip(), ">>>"]
    where = PLACEMENT.get(l.placement, l.placement)
    if l.highlights:
        rule = l.highlight_rule.strip() or "in a contrasting violet ink, slightly bolder"
        words += [f"HIGHLIGHTED WORDS (letter them exactly where they appear in the text, set apart as the book's "
                  f"learning words: {rule}; every other word in the normal lettering): "
                  + "; ".join(f"«{h}»" for h in l.highlights)]
    return "\n".join(
        ["TEXT TO LETTER (render it exactly: every word, every punctuation mark and these line breaks, "
         "nothing added, nothing left out, no misspellings):"] + [w for w in words if w] +
        [f"LETTERING: {(book.lettering or DEFAULT_LETTERING).strip()}. Use this same lettering in every image "
         f"of the book. Place the words {where}, as part of the illustration's design, sitting on calm sky, "
         "ground, water or soft light in the scene, never in a box, panel, banner, speech bubble or sign. "
         "Crisp, evenly spaced letters with strong contrast against what is behind them; body cap height "
         "about 3.5% of the image height. Keep every letter at least 8% inside each edge of the image."
         + (f" {l.note.strip()}" if l.note else "")])


TEXT_SPACE = {
    "top": "Leave the upper third calm and uncluttered (sky, wall or soft texture) because text will be "
           "printed there - no faces or important details in that area.",
    "bottom": "Leave the lower third calm and uncluttered (ground, water or soft texture) because text will "
              "be printed there - no faces or important details in that area.",
    "bubbles_top": "Leave some open space near the top of the frame for speech balloons.",
}


@dataclass
class Ref:
    path: Path
    role: str  # human-readable description used in the prompt legend


def characters_in(book: Book, explicit: list[str] | None, *texts: str) -> list[Character]:
    if explicit is not None:
        return [c for c in book.characters if c.name in explicit]
    blob = " ".join(t for t in texts if t).lower()
    return [c for c in book.characters if c.name.lower() in blob]


def compose(book: Book, scene: str, kind: str, chars: list[Character], text_space: str | None = None,
            lettering: Lettering | None = None) -> str:
    """The prompt body. The reference legend is prepended at generation time (see `with_refs`)."""
    coloring = kind == "coloring"
    parts = [f"ART STYLE: {COLORING_STYLE if coloring else book.style.strip()}"]
    if book.palette and not coloring:
        parts.append("COLOR PALETTE: " + ", ".join(book.palette) + ".")
    parts.append(f"SCENE: {scene.strip()}")
    if chars:
        parts.append("CHARACTERS (identity must stay identical across the whole book): " +
                     "; ".join(f"{c.name} - {c.description.strip()}" for c in chars))
    if lettering:
        parts.append("COMPOSITION: " + LETTERED_COMPOSITION.get(kind, COMPOSITION[kind]) + " Keep faces and key "
                     "subjects clear of the words and away from the trimmed edges.")
        parts.append(lettering_block(book, lettering))
        parts.append("RULES: " + " ".join([LETTERED_CONSTRAINT] + CONSTRAINTS[1:]))
        return "\n".join(parts)
    parts.append("COMPOSITION: " + COMPOSITION[kind] + (" " + TEXT_SPACE[text_space] if text_space else ""))
    parts.append("RULES: " + " ".join(CONSTRAINTS if kind != "character" else CONSTRAINTS[:1] + CONSTRAINTS[3:]))
    return "\n".join(parts)


def with_refs(prompt: str, refs: list[Ref], note: str | None = None, fix: str | None = None) -> str:
    """Prepend a legend telling the model what each attached image is for."""
    head = []
    if refs:
        head.append("ATTACHED IMAGES:")
        head += [f"- Image {i}: {r.role}" for i, r in enumerate(refs, 1)]
        head.append("Create a brand-new illustration of the scene below. Do not copy the reference "
                    "images' poses, backgrounds or layouts - only what each one is attached for.")
    tail = []
    if note:
        tail.append(f"ART DIRECTOR NOTE: {note.strip()}")
    if fix:
        tail.append(f"CORRECTION FROM REVIEW OF THE PREVIOUS ATTEMPT: {fix.strip()}")
    return "\n".join(head + [prompt] + tail)


def character_role(c: Character) -> str:
    return (f"character reference for {c.name}. Match {c.name}'s face, proportions, colors, markings "
            f"and clothing exactly.")


STYLE_ROLE = ("style reference only. Match its rendering technique, brushwork, line quality, color "
              "palette and lighting mood. Ignore its subject and composition.")
LETTERED_STYLE_ROLE = ("style and lettering reference (the book's cover). Match its rendering technique, "
                       "brushwork, color palette and lighting mood, and letter the words in the same lettering "
                       "style as its title (letterforms, ink color, weight). Ignore its subject, composition "
                       "and its words.")
USER_REF_ROLE = "the client's own reference for this character. Keep the identity, redraw it in the art style."


def frame_scene(book: Book) -> str:
    world = book.cover_prompt.strip().rstrip(".")
    return (f"A decorative border drawn from the world of this book ({world}): small leaves, flowers, stars "
            "or objects from the story around the four edges, light and airy, no characters.")


def reference_scene(book: Book, page) -> str:
    """A learning page's own border, drawn from the examples on that page (the words are typeset in
    the empty middle, so tables and conjugations are always spelled right)."""
    world = book.cover_prompt.strip().rstrip(".")
    examples = [l.strip().lstrip("•-*– ").strip().rstrip(".") for l in page.text.splitlines()
                if l.strip()[:1] in ("•", "-", "*", "–") and not l.strip().startswith("|")]
    if examples:
        subject = "the page's own example sentences, each as a tiny lively vignette: " + "; ".join(examples[:6])
    else:
        topic = page.chapter or (book.learning.topic if book.learning else "the lesson")
        subject = f"small playful motifs about {topic}"
    return (f"A decorative border for a learning page of this book ({world}), drawn from {subject}. "
            "The vignettes sit in the corners and along the edges, light and airy; any character stays small "
            "and at the edges, never reaching into the middle.")


def character_prompt(book: Book, c: Character) -> str:
    return compose(book, f"{c.name}: {c.description}", "character", [])
