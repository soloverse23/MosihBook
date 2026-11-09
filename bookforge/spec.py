"""book.yaml schema."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from . import kdp

BookType = Literal["picture_book", "storybook", "comic"]
PictureLayout = Literal["full_bleed", "split", "spread", "spot", "text_only"]


class Character(BaseModel):
    name: str
    description: str
    reference: Optional[str] = None  # path to a user-supplied image, relative to book.yaml


class Bubble(BaseModel):
    text: str
    speaker: Optional[str] = None
    kind: Literal["speech", "thought", "caption"] = "speech"
    position: Literal["top_left", "top_right", "bottom_left", "bottom_right", "top", "bottom"] = "top_left"


class Panel(BaseModel):
    prompt: str
    bubbles: list[Bubble] = []
    characters: Optional[list[str]] = None


class Learning(BaseModel):
    """The book's one teaching point and the writer's rule for marking it in the story."""
    topic: str = ""
    explain: str = ""
    marking: str = ""            # the writer's rule, e.g. "the adjective in violet, its opposite in parentheses after it"
    color: str = "#7A3DB8"       # highlight color of [[marked]] words on typeset pages


class MazeSpec(BaseModel):
    """A maze page: the maze itself is drawn by the software (always solvable)."""
    start: str = ""              # short visual description of who starts (drawn at the entrance)
    goal: str = ""               # short visual description of the destination (drawn at the exit)
    cols: int = Field(8, ge=3, le=20)
    rows: int = Field(10, ge=3, le=24)
    seed: int = 1


class MatchingSpec(BaseModel):
    """Draw a line from each item on the left to its partner on the right. The software shuffles the right
    column and prints the pairs on the solutions page."""
    pairs: list[tuple[str, str]] = Field(..., min_length=2, max_length=8)

    @field_validator("pairs")
    @classmethod
    def _unique(cls, v):
        for side, name in ((0, "left"), (1, "right")):
            items = [p[side].strip().lower() for p in v]
            if len(set(items)) != len(items) or not all(items):
                raise ValueError(f"matching: every {name} item must be different and non-empty "
                                 "(otherwise there is more than one correct pairing)")
        return v


class FillInItem(BaseModel):
    prompt: str                  # "___" marks where the child writes; without it a writing line follows
    answer: str


class FillInSpec(BaseModel):
    """Sentences, sums or questions the child completes (fill_in, and the main_game's exercise)."""
    items: list[FillInItem] = Field(..., min_length=1, max_length=10)


class OddGroup(BaseModel):
    items: list[str] = Field(..., min_length=3, max_length=6)
    answer: str                  # the one item that does not belong

    @model_validator(mode="after")
    def _one_answer(self) -> "OddGroup":
        norm = [x.strip().lower() for x in self.items]
        if len(set(norm)) != len(norm):
            raise ValueError(f"odd_one_out: repeated item in {self.items}")
        if norm.count(self.answer.strip().lower()) != 1:
            raise ValueError(f"odd_one_out: the answer {self.answer!r} must be one of {self.items}")
        return self


class OddOneOutSpec(BaseModel):
    groups: list[OddGroup] = Field(..., min_length=1, max_length=6)


class CertificateSpec(BaseModel):
    """The small certificate on the final challenge page, in the book's language."""
    title: str = "Well done!"
    name_label: str = "Name"
    date_label: str = "Date"


# section kinds whose page is drawn by the software: no full-page illustration, no lettering
TYPESET_KINDS = {"guided_drawing", "imagination", "solutions", "copyright", "maze"}
# kinds the software lays out from their data (the page field that holds it); answers go to the solutions page
DATA_KINDS = {"matching": "matching", "fill_in": "fill_in", "main_game": "fill_in", "odd_one_out": "odd_one_out",
              "final_challenge": "certificate"}
# kinds whose illustration is made but whose words are typeset next to it
UNLETTERED_KINDS = {"coloring", "observation"}


def plain(text: str) -> str:
    """Page text without the [[highlight]] marks: exactly the words a reader sees."""
    return text.replace("[[", "").replace("]]", "")


def highlights(text: str) -> list[str]:
    import re
    return [m.strip() for m in re.findall(r"\[\[(.+?)\]\]", text, re.S)]


class Page(BaseModel):
    """One unit of the story.

    picture_book: one page (or two facing pages for layout=spread).
    storybook:    a section of flowing text, optionally a chapter title and an illustration.
    comic:        one page of panels, or a full-page splash when `prompt` is set without panels.
    """
    text: str = ""
    prompt: Optional[str] = None
    layout: Optional[PictureLayout] = None
    text_position: Literal["top", "bottom", "auto"] = "auto"
    text_in_art: Optional[bool] = None  # None: the book's images.text_in_art
    characters: Optional[list[str]] = None
    # storybook
    chapter: Optional[str] = None
    illustration: Literal["opener", "spot"] = "spot"
    # comic
    panels: list[Panel] = []
    # structured books: the template section this page belongs to (see bookforge/templates.py)
    kind: Optional[str] = None
    maze: Optional[MazeSpec] = None
    matching: Optional[MatchingSpec] = None
    fill_in: Optional[FillInSpec] = None
    odd_one_out: Optional[OddOneOutSpec] = None
    certificate: Optional[CertificateSpec] = None

    @property
    def drawn_activity(self) -> bool:
        """A game page laid out by the software from its data (never drawn or lettered by the image model)."""
        field = DATA_KINDS.get(self.kind or "")
        return bool(field and getattr(self, field) is not None)

    @field_validator("text")
    @classmethod
    def _marks(cls, v: str) -> str:
        if v.count("[[") != v.count("]]") or "[[]]" in v:
            raise ValueError("unbalanced [[highlight]] marks in page text")
        return v


class FrontMatter(BaseModel):
    dedication: Optional[str] = None
    copyright: Optional[str] = None


class BackCover(BaseModel):
    blurb: str = ""
    prompt: Optional[str] = None  # optional separate back-cover art


class ImageSettings(BaseModel):
    provider: Literal["openai", "mock"] = "openai"
    # OpenAI's most capable model for generation + editing (reference-image consistency)
    model: str = "gpt-image-2.5-sunburst"
    # medium is ~4x cheaper than high and fine for most pages; list slots that deserve high below
    quality: Literal["low", "medium", "high", "xhigh", "max", "auto"] = "medium"
    high_quality: list[str] = []           # slot ids rendered at high quality, e.g. [cover-front]
    # OpenAI marks sizes above 2560x1440 as experimental; generate within it and upscale for print
    max_pixels: int = 2560 * 1440
    style_anchor: bool = True              # cover art is attached to every page as a style reference
    chain_previous_page: bool = False      # also attach the previous page (sequential, slower)
    # the image model letters each page's words into its illustration (and the cover's title and blurb);
    # long text-only pages are typeset inside a generated decorative frame
    text_in_art: bool = False
    # vision-model QA of every image: it only flags problems; an image is redrawn only when you ask (Redo)
    review: bool = True
    review_model: str = "gpt-5-mini"
    min_score: int = 7
    est_cost_per_image_usd: float = 0.05   # at `quality`; used only for estimates
    max_workers: int = 4


    def quality_for(self, slot_id: str) -> str:
        return "high" if slot_id in self.high_quality else self.quality

    def cost(self, slot_id: str) -> float:
        """Estimated USD for one attempt at this slot."""
        q = self.quality_for(slot_id)
        return self.est_cost_per_image_usd if q == self.quality else QUALITY_COST_USD.get(q, self.est_cost_per_image_usd)


# rough OpenAI GPT Image prices per image (1024px-class, 2026); for estimates only
QUALITY_COST_USD = {"low": 0.01, "medium": 0.05, "high": 0.21}


class Book(BaseModel):
    title: str
    subtitle: Optional[str] = None
    author: str
    language: str = "English"
    type: BookType = "picture_book"
    trim: str = "8.5x8.5"
    paper: Literal["white_bw", "cream_bw", "standard_color", "premium_color"] = "premium_color"
    style: str = Field(..., description="Art direction applied to every illustration")
    lettering: Optional[str] = None  # lettering direction for words drawn into the art (text_in_art)
    palette: list[str] = []  # optional hex colors used for text panels and cover
    characters: list[Character] = []
    pages: list[Page]
    front_matter: FrontMatter = FrontMatter()
    back_cover: BackCover = BackCover()
    cover_prompt: str
    about_author: Optional[str] = None
    page_numbers: bool = True  # print a page number on every story page
    learning: Optional[Learning] = None
    # the book follows a section structure (a template): its pages ARE the interior, no built-in front matter
    sections: list[dict] = []
    images: ImageSettings = ImageSettings()

    @field_validator("trim")
    @classmethod
    def _trim(cls, v: str) -> str:
        if v not in kdp.TRIMS:
            raise ValueError(f"trim {v!r} not a KDP size; use one of {sorted(kdp.TRIMS)}")
        return v

    @model_validator(mode="after")
    def _check(self) -> "Book":
        names = {c.name for c in self.characters}
        for i, p in enumerate(self.pages, 1):
            for n in (p.characters or []) + [n for pn in p.panels for n in (pn.characters or [])]:
                if n not in names:
                    raise ValueError(f"page {i}: unknown character {n!r}")
            if p.kind == "maze" and p.maze is None:
                p.maze = MazeSpec(seed=i)
            if self.type == "comic" and len(p.panels) > 6:
                raise ValueError(f"page {i}: at most 6 panels per comic page")
        return self

    def lettered(self, page: "Page") -> bool:
        """Are this page's words drawn into its illustration by the image model?"""
        if page.kind in TYPESET_KINDS or page.kind in UNLETTERED_KINDS or page.drawn_activity:
            return False
        on = self.images.text_in_art if page.text_in_art is None else page.text_in_art
        return bool(on and self.type != "comic" and page.prompt and (page.text.strip() or page.chapter))

    @property
    def structured(self) -> bool:
        return bool(self.sections)

    @property
    def trim_size(self) -> tuple[float, float]:
        return kdp.parse_trim(self.trim)


def load(path: str | Path) -> Book:
    return Book.model_validate(yaml.safe_load(Path(path).read_text()))
