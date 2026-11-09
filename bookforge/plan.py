"""Stage 1: turn book.yaml into the list of illustrations ("slots") the book needs."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import kdp
from .art import prompting
from .art.prompting import Lettering
from .characters import char_id
from .layout import geometry
from .spec import TYPESET_KINDS, Book, highlights, plain


@dataclass
class Slot:
    id: str
    kind: str                  # key into prompting.COMPOSITION
    prompt: str                # fully composed prompt sent to the model
    aspect: float              # width / height of the printed box
    characters: list[str] = field(default_factory=list)
    user_reference: str | None = None
    lettering: Lettering | None = None  # words the model letters into this image (text_in_art)

    @property
    def expected_text(self) -> str:
        """Every word the image must carry, in reading order, for the reviewer to check."""
        if not self.lettering:
            return ""
        return "\n".join(t.strip() for t in (self.lettering.heading or "", self.lettering.text) if t.strip())


def picture_layout(book: Book, i: int) -> str:
    p = book.pages[i]
    if p.layout:
        return p.layout
    return "full_bleed" if p.prompt else "text_only"


def text_space(p, layout: str) -> str:
    if p.text_position != "auto":
        return p.text_position
    return "top" if layout == "spread" else "bottom"


def split_chapter(chapter: str) -> tuple[str, str]:
    """'Chapter 1: A Hat from the Sky' -> ('Chapter 1', 'A Hat from the Sky')."""
    kicker, _, title = chapter.partition(": ")
    return ("", kicker) if not title else (kicker, title)


def page_lettering(p, book: Book | None = None) -> Lettering:
    """The words lettered into a page: the plain text, with its [[marked]] words to highlight."""
    heading = "\n".join(x for x in split_chapter(p.chapter) if x) if p.chapter else None
    rule = book.learning.marking if book and book.learning else ""
    return Lettering(plain(p.text), heading, p.text_position, highlights=tuple(highlights(p.text)),
                     highlight_rule=rule)


def coloring_aspect(interior: kdp.Interior, page_no: int = 1) -> float:
    """The coloring picture fills the safe area under the typeset instruction."""
    _, _, w, h = interior.safe_box(page_no)
    return w / (h - COLORING_HEAD)


COLORING_HEAD = 1.3  # inches at the top of a coloring page for its title and instruction


def needs_text_frame(book: Book) -> bool:
    """Long text-only pages are typeset inside one generated decorative frame (text_in_art books)."""
    if not book.images.text_in_art or book.type == "comic":
        return False
    return any(p.text.strip() and (not p.prompt or p.kind in ("solutions", "copyright")) for p in book.pages
               if p.kind not in ("maze", "guided_drawing", "imagination") and not p.drawn_activity)


def plan(book: Book, pages_hint: int = kdp.MIN_PAGES) -> list[Slot]:
    tw, th = book.trim_size
    interior = kdp.Interior(tw, th, pages_hint)
    page_aspect = interior.page_w / interior.page_h
    slots: list[Slot] = []

    for c in book.characters:
        slots.append(Slot(char_id(c.name), "character",
                          prompting.character_prompt(book, c), 2 / 3, user_reference=c.reference))

    def add(slot_id, kind, scene, aspect, explicit, text, space=None, lettering=None):
        chars = prompting.characters_in(book, explicit, scene, text)
        slots.append(Slot(slot_id, kind, prompting.compose(book, scene, kind, chars, space, lettering), aspect,
                          [c.name for c in chars], lettering=lettering))

    for i, p in enumerate(book.pages, 1):
        sid = f"p{i:03d}"
        lettered = book.lettered(p)
        if p.kind == "maze" and p.maze:  # the maze is drawn in code; the art is its two ends
            hero = book.characters[0].name if book.characters else "a friendly child"
            add(f"{sid}-start", "maze_end", p.maze.start or f"{hero}, ready to set off, full body", 1.0,
                p.characters, p.maze.start)
            add(f"{sid}-goal", "maze_end", p.maze.goal or "a small treasure chest", 1.0, p.characters or [],
                p.maze.goal)
            continue
        if p.kind in TYPESET_KINDS:  # drawn by the layout, no illustration
            continue
        if p.drawn_activity:  # laid out from its data; the picture is at most a small vignette beside it
            if p.prompt and p.kind != "final_challenge":
                add(sid, "maze_end", p.prompt, 1.0, p.characters, "")
            continue
        if p.kind == "coloring" and p.prompt:
            add(sid, "coloring", p.prompt, coloring_aspect(interior), p.characters, p.text)
            continue
        if p.kind == "observation" and p.prompt:
            add(sid, "observation", p.prompt, page_aspect, p.characters, p.text)
            continue
        if book.type == "picture_book":
            layout = picture_layout(book, i - 1)
            if layout == "text_only" or not p.prompt:
                continue
            if lettered:  # the model draws the whole page, words included
                aspect = interior.spread_w / interior.page_h if layout == "spread" else page_aspect
                add(sid, layout, p.prompt, aspect, p.characters, p.text, lettering=page_lettering(p, book))
                continue
            aspect = {
                "full_bleed": page_aspect,
                "split": interior.page_w / (interior.page_h * geometry.SPLIT_IMAGE_FRACTION),
                "spread": interior.spread_w / interior.page_h,
                "spot": geometry.PICTURE_SPOT_ASPECT,
            }[layout]
            space = text_space(p, layout) if p.text and layout in ("full_bleed", "spread") else None
            add(sid, layout, p.prompt, aspect, p.characters, p.text, space)
        elif book.type == "storybook":
            if p.prompt and lettered:
                add(sid, p.illustration, p.prompt, page_aspect, p.characters, p.text, lettering=page_lettering(p, book))
            elif p.prompt:
                opener = p.illustration == "opener"
                aspect = page_aspect if opener else geometry.STORY_SPOT_ASPECT
                # the page's words are printed on an opener, so its prompt keeps their band calm
                space = text_space(p, "full_bleed") if opener and (p.text.strip() or p.chapter) else None
                add(sid, p.illustration, p.prompt, aspect, p.characters, p.text, space)
        else:  # comic
            if p.panels:
                boxes = geometry.panel_boxes(len(p.panels), interior.safe_box(1))
                for k, (panel, box) in enumerate(zip(p.panels, boxes), 1):
                    space = "bubbles_top" if panel.bubbles else None
                    add(f"{sid}-{k}", "panel", panel.prompt, box[2] / box[3], panel.characters,
                        " ".join(b.text for b in panel.bubbles), space)
            elif p.prompt:
                add(sid, "full_bleed", p.prompt, page_aspect, p.characters, p.text,
                    "bottom" if p.text else None)

    lettered_cover = book.images.text_in_art
    if needs_text_frame(book):
        add("text-frame", "frame", prompting.frame_scene(book), page_aspect, [], "")
    if lettered_cover and book.type != "comic" and book.characters and not book.structured:
        hero = book.characters[0].name
        add("the-end", "spot", f"A small, warm closing vignette: {hero} waving goodbye, a few motifs from the "
            "story around them", page_aspect, [hero], "", lettering=Lettering("The End", None, "below the vignette"))

    cover_aspect = (tw + kdp.BLEED) / (th + 2 * kdp.BLEED)
    cover_l = Lettering(
        "\n".join(x for x in (book.subtitle, book.author) if x), book.title, "top",
        note="The title is the largest lettering, across the top area; "
             + (f"the subtitle '{book.subtitle}' smaller just under it; " if book.subtitle else "")
             + f"the author's name '{book.author}' small and centered near the bottom.") if lettered_cover else None
    add("cover-front", "cover", book.cover_prompt, cover_aspect, None, book.cover_prompt, lettering=cover_l)
    if lettered_cover and (book.back_cover.blurb or book.back_cover.prompt):
        back_w = kdp.BLEED + tw
        gap_w = round((kdp.BARCODE_INSET + kdp.BARCODE_W) / back_w * 100 + 4)
        gap_h = round((kdp.BLEED + kdp.BARCODE_INSET + kdp.BARCODE_H) / (th + 2 * kdp.BLEED) * 100 + 3)
        scene = book.back_cover.prompt or ("A quiet, low-detail continuation of the front cover's world "
                                           f"({book.cover_prompt.strip()}), with soft open space for the words")
        back_l = Lettering(book.back_cover.blurb, None, "in the upper two-thirds",
                           note=f"Leave the bottom-right corner, {gap_w}% of the image width and {gap_h}% of its "
                                "height measured from the right and bottom edges, as plain calm flat color with "
                                "no letters or details: a barcode is printed there.") if book.back_cover.blurb else None
        add("cover-back", "back", scene, cover_aspect, None, "", lettering=back_l)
    elif book.back_cover.prompt:
        add("cover-back", "back", book.back_cover.prompt, cover_aspect, None, "")
    return slots
