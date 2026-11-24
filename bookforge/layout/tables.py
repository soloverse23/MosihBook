"""Learning pages typeset from their text: markdown tables become real tables, bullets a tidy list.

The author writes reference material as plain text (a caption line, a `| a | b |` table, "Dans l'histoire :"
and a few `•` examples). Printed raw, the pipes and `|---|` rows showed on the page; here every part gets
its own look, sized to the width the page's art leaves free.
"""
from __future__ import annotations

import re

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

from .base import Sheet, marked

_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
BULLET = ("•", "-", "*", "–")
MIN_TEXT = 9.5  # points: the smallest prose or list text of a learning page


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_table_line(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().count("|") >= 2


def has_table(text: str) -> bool:
    return any(is_table_line(x) for x in (text or "").splitlines())


class TableBlock(Flowable):
    """A table that takes whatever width it is given: header row on the accent color, pronoun column
    in the accent, rows on alternating soft tints, cells wrapping instead of overflowing."""

    SIZE = 10        # points at scale 1
    MIN_SIZE = 8     # points, at any scale: the font may shrink this far so every word fits its cell whole
    PAD = 5          # points of cell padding left and right, at scale 1
    AIR = 1.3        # a table is set this much wider than its one-line cells, never across the whole page

    ARROW = "→"

    def __init__(self, sheet: Sheet, rows: list[list[str]], scale: float = 1.0, open_style: bool = False):
        super().__init__()
        self.sheet, self.scale, self.open = sheet, scale, open_style
        n = max(len(r) for r in rows)
        self.rows = [r + [""] * (n - len(r)) for r in rows]
        if open_style and n == 2:  # a pair reads as "love → loves": an arrow column between the two
            self.rows = [[r[0], "" if i == 0 else self.ARROW, r[1]] for i, r in enumerate(self.rows)]
            n = 3
        self.n = n
        self.size0 = max(self.SIZE * scale, self.MIN_SIZE)  # a smaller page scale never goes below MIN_SIZE
        self.min_size = self.MIN_SIZE
        words, lines = self._measure(self.size0)
        # inches it cannot go below: the longest word of each column, whole, at the smallest font
        self.min_w = sum(self._measure(self.min_size)[0]) / inch + 0.02
        one_line = sum(lines) / inch + 0.02
        # its measure: a two-column table of short words stays a compact table in the middle of the page,
        # it is not stretched to the page's width with its words lost far apart
        self.max_w = max(self.min_w, min(6.4, max(one_line * self.AIR, 2.4)))
        # inches it would like (see shaped._natural): every cell on one line, when the page allows
        self.want = min(self.max_w, one_line)
        self.spaceAfter = 10 * scale
        self.hAlign = "CENTER"

    def _measure(self, size: float) -> tuple[list[float], list[float]]:
        """Per column, in points with padding: the widest single word, and the widest whole cell on one line."""
        t = self.sheet.theme
        pad = 2 * self.PAD * self.scale
        words, lines = [pad] * self.n, [pad] * self.n
        for i, r in enumerate(self.rows):
            font = t.heading if i == 0 else t.body
            for j, c in enumerate(r):
                plain = c.replace("[[", "").replace("]]", "")
                for w in re.split(r"[ \t\n]+", plain.strip()):  # a no-break space holds its words together
                    words[j] = max(words[j], stringWidth(w, font, size) + pad)
                lines[j] = max(lines[j], stringWidth(plain, font, size) + pad)
        return words, lines

    def _layout(self, aw: float) -> tuple[float, list[float]]:
        """The font size and column widths for `aw` points: the largest size (down to MIN_SIZE) at which each
        column holds its longest word whole; the room left goes first to the columns whose cells would
        otherwise wrap, then evenly. No word is ever cut inside a cell."""
        s = self.scale
        size = self.size0
        while True:
            words, lines = self._measure(size)
            if sum(words) <= aw or size <= self.min_size:
                break
            size -= 0.25 * s
        widths = list(words)
        extra = aw - sum(widths)
        if extra > 0:
            short = [l - w for w, l in zip(words, lines)]  # what each column lacks to set its cells on one line
            gap = sum(short)
            if gap > 0:
                give = min(extra, gap)
                widths = [w + give * d / gap for w, d in zip(widths, short)]
                extra -= give
            widths = [w + extra / self.n for w in widths]
        return size, widths

    def _open_table(self, aw: float) -> Table:
        """No box, no fills: a header in small accent capitals over a rule, rows on hairlines, the word and
        its form set in the accent and the ink, a pair joined by an arrow."""
        t, s = self.sheet.theme, self.scale
        color = self.sheet.mark_color
        size, widths = self._layout(aw)
        pair = self.n == 3 and all(r[1] in ("", self.ARROW) for r in self.rows)
        head = self.sheet.style(size * 0.86, font=t.heading, align=TA_CENTER, color=t.accent, leading=1.2,
                                splitLongWords=0)
        head_r = self.sheet.style(size * 0.86, font=t.heading, align=TA_RIGHT, color=t.accent, leading=1.2,
                                  splitLongWords=0)
        head_l = self.sheet.style(size * 0.86, font=t.heading, align=TA_LEFT, color=t.accent, leading=1.2,
                                  splitLongWords=0)
        lead = self.sheet.style(size * 1.08, font=t.heading, align=TA_RIGHT if pair else TA_LEFT,
                                color=t.accent, leading=1.25, splitLongWords=0)
        cell = self.sheet.style(size * 1.08, align=TA_LEFT if pair else TA_CENTER, leading=1.25, splitLongWords=0)
        arrow = self.sheet.style(size * 1.1, align=TA_CENTER, color=t.accent, leading=1.25)
        for st in (head, head_r, head_l, lead, cell, arrow):
            st.spaceAfter = 0
        data = []
        for i, r in enumerate(self.rows):
            if i == 0:
                data.append([Paragraph(marked(c.upper() if len(c) < 40 else c, color),
                                       head_r if pair and j == 0 else head_l if pair and j == 2 else head)
                             for j, c in enumerate(r)])
            else:
                data.append([Paragraph(marked(c, color), arrow if pair and j == 1 else lead if j == 0 else cell)
                             for j, c in enumerate(r)])
        tint = HexColor(t.accent)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), t.body),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5 * s), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5 * s),
            ("LEFTPADDING", (0, 0), (-1, -1), self.PAD * s), ("RIGHTPADDING", (0, 0), (-1, -1), self.PAD * s),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, tint),
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, Color(tint.red, tint.green, tint.blue, alpha=0.28)),
        ]
        tab = Table(data, colWidths=widths, repeatRows=1)
        tab.setStyle(TableStyle(style))
        return tab

    def _table(self, aw: float) -> Table:
        if self.open:
            return self._open_table(aw)
        t, s = self.sheet.theme, self.scale
        color = self.sheet.mark_color
        size, widths = self._layout(aw)
        # a word is never split across two lines of a cell (it would read "chantio / ns")
        head = self.sheet.style(size, font=t.heading, align=TA_CENTER, color="#FFFFFF", leading=1.2,
                                splitLongWords=0)
        lead = self.sheet.style(size, align=TA_LEFT, color=t.accent, leading=1.25, splitLongWords=0)
        cell = self.sheet.style(size, align=TA_CENTER, leading=1.25, splitLongWords=0)
        for st in (head, lead, cell):
            st.spaceAfter = 0
        data = []
        for i, r in enumerate(self.rows):
            if i == 0:
                data.append([Paragraph(marked(c, color), head) for c in r])
            else:
                data.append([Paragraph(marked(c, color), lead if j == 0 else cell) for j, c in enumerate(r)])
        tint = HexColor(t.accent)
        soft = Color(tint.red, tint.green, tint.blue, alpha=0.08)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), t.body),  # ReportLab's default Helvetica is never embedded
            ("BACKGROUND", (0, 0), (-1, 0), tint),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5 * s), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * s),
            ("LEFTPADDING", (0, 0), (-1, -1), self.PAD * s), ("RIGHTPADDING", (0, 0), (-1, -1), self.PAD * s),
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, Color(tint.red, tint.green, tint.blue, alpha=0.25)),
            ("BOX", (0, 0), (-1, -1), 0.8, tint),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]
        for i in range(1, len(data)):
            style.append(("BACKGROUND", (0, i), (-1, i), soft if i % 2 else Color(1, 1, 1, alpha=0.85)))
        tab = Table(data, colWidths=widths, repeatRows=1)
        tab.setStyle(TableStyle(style))
        return tab

    def wrap(self, aw, ah):
        aw = min(aw, self.max_w * inch)  # poured into a wide frame, it keeps its own measure, centred
        self._t = self._table(aw)
        self.width, self.height = self._t.wrap(aw, ah)
        return self.width, self.height

    def draw(self):
        self._t.drawOn(self.canv, 0, 0)

    def split(self, aw, ah):
        """Too tall for what is left of the page: it continues on the next one, its header row repeated."""
        return self._table(min(aw, self.max_w * inch)).split(aw, ah)


_RULE = re.compile(r"^([^:|]{2,26}?)\s*:\s+(\S.*)$")  # "Add -s: most verbs just add -s." -> label, sentence


def learning_page(sheet: Sheet, text: str, scale: float = 1.0, open_style: bool = False) -> list:
    """Reference text -> flowables: caption lines over tables, labels ("... :"), bullet lists, prose.

    `open_style`: the designed lesson page: tables without a box, and "Label: sentence" lines set as quiet
    left-aligned rules (the label in the accent) instead of centred lines."""
    from ..words import typeset
    t = sheet.theme
    color = sheet.mark_color
    text = typeset(text, t.language)  # French « » : ; ! ? never left alone at a line's end
    # a child reads these: a smaller page scale never sets them below a readable size
    caption = sheet.style(max(13.5 * scale, 11.5), font=t.heading, align=TA_CENTER, color=t.accent, leading=1.2)
    caption.spaceAfter = 6 * scale
    label = sheet.style(max(11.5 * scale, 10), font=t.heading, align=TA_CENTER, leading=1.2)
    label.spaceAfter = 4 * scale
    prose = sheet.style(max(t.size * scale, MIN_TEXT), align=TA_CENTER, leading=1.45)
    prose.spaceAfter = 8 * scale
    item = sheet.style(max(t.size * scale, MIN_TEXT), align=TA_LEFT, leading=1.5)
    item.spaceAfter = 8 * scale
    rule = sheet.style(max(t.size * scale, MIN_TEXT), align=TA_LEFT, leading=1.45, leftIndent=12 * scale,
                       firstLineIndent=-12 * scale)
    rule.spaceAfter = 7 * scale

    lines = [l.rstrip() for l in text.strip().splitlines()]
    out, k = [], 0
    while k < len(lines):
        line = lines[k].strip()
        if not line:
            k += 1
            continue
        if is_table_line(line):
            rows = []
            while k < len(lines) and is_table_line(lines[k]):
                if not _SEP.match(lines[k].strip()):
                    rows.append(_cells(lines[k]))
                k += 1
            out.append(TableBlock(sheet, rows, scale, open_style))
            continue
        if line.startswith(BULLET):
            items = []
            while k < len(lines) and lines[k].strip().startswith(BULLET):
                items.append(marked(lines[k].strip().lstrip("•-*– ").strip(), color))
                k += 1
            dot = f'<font color="{t.accent}">•</font>&nbsp;&nbsp;'
            para = Paragraph("<br/>".join(dot + x for x in items), item)
            para.wrap(6.4 * inch, 1e6)  # a list is as wide as its longest line, centred as a block (shaped)
            para.max_w = min(6.4, max(para.getActualLineWidths0() or [0]) / inch + 0.1)
            out.append(para)
            continue
        nxt = next((lines[j] for j in range(k + 1, len(lines)) if lines[j].strip()), "")
        if is_table_line(nxt):
            out.append(Paragraph(marked(line, color), caption))
        elif line.endswith(":") and len(line) < 60:
            out.append(Paragraph(marked(line, color), label))
        elif open_style and (m := _RULE.match(line)) and not is_table_line(line):
            out.append(Paragraph(f'<font name="{t.heading}" color="{t.accent}">{marked(m.group(1), color)}</font>'
                                 f'&nbsp;&nbsp;{marked(m.group(2), color)}', rule))
        else:
            out.append(Paragraph(marked(line, color), prose))
        k += 1
    return out
