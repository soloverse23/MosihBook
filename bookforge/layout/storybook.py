"""Illustrated storybook interiors: flowing book typography with chapter openers and spot art."""
from __future__ import annotations

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Frame, Paragraph, Spacer
from reportlab.platypus.flowables import ImageAndFlowables
from xml.sax.saxutils import escape

from .. import kdp
from ..project import Project
from ..plan import needs_text_frame, split_chapter, text_space
from ..spec import TYPESET_KINDS, Page
from . import front_matter as fm
from . import activities
from .base import FOLIO_SPACE, Sheet, frame_box, marked, para_html, text_band
from .geometry import ILLUSTRATED_ART_FRACTIONS, STORY_SPOT_ASPECT


class SpotArt(Flowable):
    def __init__(self, sheet: Sheet, src, width_in: float):
        super().__init__()
        self.sheet, self.src = sheet, src
        self.w_in, self.h_in = width_in, width_in / STORY_SPOT_ASPECT

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, (self.h_in + 0.3) * inch

    def draw(self):  # canvas is already translated to the flowable's origin
        self.sheet.image(self.src, ((self._aw / inch - self.w_in) / 2, 0.15, self.w_in, self.h_in))


HEAD_SPACE = 0.34  # inches reserved at the top of the safe area for the running head


class Ornament(Flowable):
    """Short rule - dot - rule, centered under chapter titles."""
    def __init__(self, color: str):
        super().__init__()
        self.color = color

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, 0.45 * inch

    def draw(self):
        c, cx, y = self.canv, self._aw / 2, 0.25 * inch
        c.setStrokeColor(HexColor(self.color))
        c.setFillColor(HexColor(self.color))
        c.setLineWidth(0.6)
        c.line(cx - 0.7 * inch, y, cx - 0.1 * inch, y)
        c.line(cx + 0.1 * inch, y, cx + 0.7 * inch, y)
        c.circle(cx, y, 0.035 * inch, stroke=0, fill=1)


class DropCap(Flowable):
    """A large initial spanning three lines of body text."""
    def __init__(self, letter: str, font: str, body_size: float, leading: float, color: str):
        super().__init__()
        self.letter, self.font, self.color = letter, font, color
        self.size = leading * 2 + body_size * 0.95
        self.h = leading * 3 - (leading - body_size)

    def wrap(self, aw, ah):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        self.w = stringWidth(self.letter, self.font, self.size)
        return self.w, self.h

    # ImageAndFlowables treats its first argument like an Image
    def _restrictSize(self, aw, ah):
        return self.wrap(aw, ah)

    def _unRestrictSize(self):
        pass

    def draw(self):
        self.canv.setFont(self.font, self.size)
        self.canv.setFillColor(HexColor(self.color))
        self.canv.drawString(0, self.h - self.size * 0.74, self.letter)


def drop_cap(text: str, style, theme) -> Flowable:
    if not text[:1].isalpha():
        return Paragraph(text, style)
    cap = DropCap(text[0], theme.heading, style.fontSize, style.leading, theme.accent)
    words = text[1:].split(" ", 1)  # rest of the first word in small caps feel
    rest = f"{words[0].upper()} {words[1] if len(words) > 1 else ''}"
    return ImageAndFlowables(cap, [Paragraph(rest, style)], imageSide="left", imageRightPadding=4,
                             imageBottomPadding=0)


def running_head(sheet: Sheet, interior: kdp.Interior, text: str) -> None:
    x, y, w, h = interior.safe_box(sheet.page_no)
    c = sheet.c
    c.setFont(sheet.theme.body, 7.5)
    c.setFillColor(HexColor(sheet.theme.ink))
    c.drawCentredString((x + w / 2) * inch, (y + h - 0.1) * inch, text.upper(), charSpace=1.4)


def spaced_caps(text: str) -> str:
    return "&nbsp;&nbsp;&nbsp;".join(" ".join(word) for word in escape(text.upper()).split())


# children read the words on the picture: larger than the flowing body text, never below the floor
ILLUSTRATED_SIZE = 15
ILLUSTRATED_MIN = 12
PANEL = {"band": 0.36, "grow_to": 0.55, "width": 0.86}
PANEL_STYLE = {"align": TA_CENTER, "autoLeading": "max"}  # the chapter title is larger than the body


def _panel_html(p: Page, sheet: Sheet) -> str:
    head = ""
    if p.chapter:
        kicker, title = split_chapter(p.chapter)
        if kicker:
            head += f'<font size="9.5" color="{sheet.theme.accent}">{spaced_caps(kicker)}</font><br/>'
        head += f'<font name="{sheet.theme.heading}" size="22">{escape(title)}</font><br/><br/>'
    return head + para_html(p.text, sheet.mark_color) if p.text.strip() else head.removesuffix("<br/><br/>")


def _fits(sheet: Sheet, interior: kdp.Interior, html: str, w: float, h: float) -> bool:
    try:
        sheet.fit_paragraph(html, w, h, ILLUSTRATED_SIZE, min_size=ILLUSTRATED_MIN, **PANEL_STYLE)
        return True
    except ValueError:
        return False


def _fade(sheet: Sheet, y: float, h: float) -> None:
    """Paper-colored gradient over the bottom `h` inches of art that ends at `y`."""
    c, paper, steps = sheet.c, HexColor(sheet.theme.paper), 40
    c.saveState()
    for k in range(steps):
        c.setFillColor(Color(paper.red, paper.green, paper.blue, alpha=(k + 1) / steps))
        c.rect(0, (y + h * (steps - k - 1) / steps) * inch, sheet.page_size[0] * inch, h / steps * inch + 0.5,
               stroke=0, fill=1)
    c.restoreState()


def illustrated_page(sheet: Sheet, interior: kdp.Interior, p: Page, src) -> None:
    """Picture and words on one page: full-bleed art with the text on a panel in the calm band
    the prompt kept clear. Text too long for the panel gets the art on top fading into the paper."""
    html = _panel_html(p, sheet)
    x, y, w, h = safe = interior.safe_box(sheet.page_no)
    if not html or _fits(sheet, interior, html, w * PANEL["width"] - 0.6, h * PANEL["grow_to"] - 0.6):
        sheet.image(src, (0, 0, interior.page_w, interior.page_h))
        text_band(sheet, interior, html, text_space(p, "full_bleed"), ILLUSTRATED_SIZE,
                  min_size=ILLUSTRATED_MIN, **PANEL, **PANEL_STYLE)
        return
    for frac in ILLUSTRATED_ART_FRACTIONS:
        art_h = interior.page_h * frac
        text_h = interior.page_h - art_h - y + 0.35  # the fade's lower part is paper already
        if _fits(sheet, interior, html, w, text_h) or frac == ILLUSTRATED_ART_FRACTIONS[-1]:
            break
    sheet.paper()
    sheet.image(src, (0, interior.page_h - art_h, interior.page_w, art_h))
    _fade(sheet, interior.page_h - art_h, min(1.2, art_h * 0.25))
    sheet.text(html, (x, y, w, text_h), ILLUSTRATED_SIZE, valign="top", safe=safe,
               min_size=ILLUSTRATED_MIN, **PANEL_STYLE)


def _finds(project: Project) -> dict[str, list[str]]:
    """Observation pages: the find-list read from each finished picture (see art.generate)."""
    import json
    from ..art.review import find_list
    f = project.build / ("observation-mock.json" if project.mock else "observation.json")
    data = json.loads(f.read_text()) if f.exists() else {}
    return {k: find_list(v.get("items", [])) for k, v in data.items()}


def render(sheet: Sheet, interior: kdp.Interior, project: Project) -> None:
    book = project.book
    t = sheet.theme
    body = sheet.style(t.size, leading=1.45)
    body.firstLineIndent = t.size * 1.5
    body.spaceAfter = 0
    first = sheet.style(t.size, leading=1.45)
    first.spaceAfter = 0
    heading = sheet.style(24, font=t.heading, align=TA_CENTER, leading=1.15)
    heading.spaceAfter = 4
    label = sheet.style(9, align=TA_CENTER, color=t.accent)
    label.spaceAfter = 8

    state = {"frame": None, "chapter": book.title, "opening": False}
    # text_in_art books: text pages are typeset inside a generated decorative frame
    frame_art = project.art_path("text-frame") if needs_text_frame(book) else None

    def text_box():
        if frame_art:
            return frame_box(interior, sheet.page_no)
        x, y, w, h = interior.safe_box(sheet.page_no)
        return x, y + FOLIO_SPACE, w, h - FOLIO_SPACE - HEAD_SPACE

    def ensure_frame():
        if state["frame"] is None:
            if frame_art:
                sheet.image(frame_art, (0, 0, interior.page_w, interior.page_h))
            else:
                sheet.paper()
            x, y, w, h = box = text_box()
            state["frame"] = Frame(x * inch, y * inch, w * inch, h * inch, 0, 0, 0, 0)
            sheet.records["text"].append({"page": sheet.page_no, "box": list(box),
                                          "safe": list(interior.safe_box(sheet.page_no))})

    def end_page():
        if state["frame"] is not None:
            if not state["opening"] and not frame_art:  # chapter openers and framed pages carry no running head
                running_head(sheet, interior, book.title if sheet.page_no % 2 == 0 else state["chapter"])
            state["opening"] = False
            if book.page_numbers:
                sheet.folio(interior, on_art=bool(frame_art))
            sheet.new_page()
            state["frame"] = None

    def pour(flowables):
        while flowables:
            ensure_frame()
            state["frame"].addFromList(flowables, sheet.c)
            if flowables:
                end_page()

    def full_page(draw):
        end_page()
        draw(sheet, interior, book)
        sheet.new_page()

    sheet.mark_color = book.learning.color if book.learning else None
    if not book.structured:  # a template book's own pages are its whole interior (it has its own copyright page)
        full_page(lambda s, i, b: fm.title_page(s, i, b, project.art_path("cover-front")))
        full_page(fm.copyright_page)
        if book.front_matter.dedication:
            full_page(fm.dedication_page)
    finds = _finds(project)

    def activity(draw):
        end_page()
        draw()
        if book.page_numbers:
            sheet.folio(interior, on_art=True)
        sheet.new_page()

    for n, p in enumerate(book.pages, 1):
        src = project.art_path(f"p{n:03d}")
        flow = []
        if p.kind == "maze" and p.maze:
            activity(lambda: activities.maze_page(sheet, interior, book, p, project.art_path(f"p{n:03d}-start"),
                                                  project.art_path(f"p{n:03d}-goal")))
            continue
        if p.kind in ("guided_drawing", "imagination"):
            activity(lambda: activities.drawing_page(sheet, interior, book, p))
            continue
        if p.kind == "coloring" and p.prompt:
            activity(lambda: activities.coloring_page(sheet, interior, book, p, src))
            continue
        if p.drawn_activity:  # games laid out from their data, with an optional small vignette
            vig = src if p.prompt else None
            if p.kind == "final_challenge":
                activity(lambda: activities.final_challenge_page(sheet, interior, book, p))
            elif p.matching:
                activity(lambda: activities.matching_page(sheet, interior, book, p, n, vig))
            elif p.fill_in:
                activity(lambda: activities.fill_in_page(sheet, interior, book, p, vig))
            else:
                activity(lambda: activities.odd_one_out_page(sheet, interior, book, p, vig))
            continue
        if p.kind == "observation" and p.prompt:
            items = finds.get(f"p{n:03d}", [])
            p = p.model_copy(update={"text": p.text.rstrip() + ("\n" + "  ·  ".join(items) if items else "")})
        if p.kind in TYPESET_KINDS:
            p = p.model_copy(update={"prompt": None})
        if book.structured and not p.prompt:
            end_page()  # every page of a template book starts on its own page
        if book.lettered(p):  # the image model lettered the words into the picture: the page is the art
            end_page()
            if p.chapter:
                state["chapter"] = split_chapter(p.chapter)[1]
            sheet.image(src, (0, 0, interior.page_w, interior.page_h))
            if book.page_numbers:
                sheet.folio(interior, on_art=True)
            sheet.new_page()
            continue
        if p.prompt and p.illustration == "opener":
            end_page()
            if p.chapter:
                state["chapter"] = split_chapter(p.chapter)[1]
            illustrated_page(sheet, interior, p, src)
            if book.page_numbers:
                sheet.folio(interior, on_art=True)
            sheet.new_page()
            continue
        if p.chapter:
            end_page()
            ensure_frame()
            state["opening"] = True
            kicker, title = split_chapter(p.chapter)
            state["chapter"] = title
            flow.append(Spacer(1, text_box()[3] * inch * 0.14))
            if kicker:
                flow.append(Paragraph(spaced_caps(kicker), label))
            flow += [Paragraph(escape(title), heading), Ornament(t.accent)]
        if p.prompt and p.illustration == "spot":
            flow.append(SpotArt(sheet, src, text_box()[2] * 0.72))
        for k, para in enumerate(x for x in p.text.split("\n\n") if x.strip()):
            text = marked(para.strip(), sheet.mark_color).replace("\n", "<br/>" if book.structured else " ")
            if k == 0 and p.chapter and p.kind in (None, "story"):
                flow.append(drop_cap(text, first, t))
            else:
                style = first if (k == 0 and p.prompt and p.illustration == "spot") else body
                flow.append(Paragraph(text, style))
        if p.kind == "solutions":
            flow += activities.answers(sheet, book)
        pour(flow)
    end_page()
    if book.images.text_in_art and book.characters and not book.structured:
        full_page(lambda s, i, b: fm.the_end_page(s, i, b, project.art_path("the-end")))

    if book.about_author and not book.structured:
        full_page(fm.about_page)
    count = sheet.page_no - 1
    for _ in range(kdp.pad_page_count(count) - count):
        full_page(fm.blank_page)
