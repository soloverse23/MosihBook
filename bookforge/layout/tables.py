"""Learning pages typeset from their text: markdown tables become real tables, bullets a tidy list.

The author writes reference material as plain text (a caption line, a `| a | b |` table, "Dans l'histoire :"
and a few `•` examples). Printed raw, the pipes and `|---|` rows showed on the page; here every part gets
its own look, sized to the width the page's art leaves free.
"""
from __future__ import annotations

import re

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

from .base import Sheet, marked

_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
BULLET = ("•", "-", "*", "–")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_table_line(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().count("|") >= 2


class TableBlock(Flowable):
    """A table that takes whatever width it is given: header row on the accent color, pronoun column
    in the accent, rows on alternating soft tints, cells wrapping instead of overflowing."""

    SIZE = 10        # points at scale 1
    MIN_SIZE = 7.5   # points at scale 1: the font may shrink this far so every word fits its cell whole
    PAD = 3          # points of cell padding left and right, at scale 1

    def __init__(self, sheet: Sheet, rows: list[list[str]], scale: float = 1.0):
        super().__init__()
        self.sheet, self.scale = sheet, scale
        n = max(len(r) for r in rows)
        self.rows = [r + [""] * (n - len(r)) for r in rows]
        self.n = n
        self.max_w = 6.4
        words, lines = self._measure(self.SIZE * scale)
        # inches it would like (see shaped._natural): every cell on one line, when the page allows
        self.want = min(self.max_w, sum(lines) / inch + 0.02)
        # inches it cannot go below: the longest word of each column, whole, at the smallest font
        self.min_w = sum(self._measure(self.MIN_SIZE * scale)[0]) / inch + 0.02
        self.spaceAfter = 10 * scale

    def _measure(self, size: float) -> tuple[list[float], list[float]]:
        """Per column, in points with padding: the widest single word, and the widest whole cell on one line."""
        t = self.sheet.theme
        pad = 2 * self.PAD * self.scale
        words, lines = [pad] * self.n, [pad] * self.n
        for i, r in enumerate(self.rows):
            font = t.heading if i == 0 else t.body
            for j, c in enumerate(r):
                plain = c.replace("[[", "").replace("]]", "")
                for w in plain.split():
                    words[j] = max(words[j], stringWidth(w, font, size) + pad)
                lines[j] = max(lines[j], stringWidth(plain, font, size) + pad)
        return words, lines

    def _layout(self, aw: float) -> tuple[float, list[float]]:
        """The font size and column widths for `aw` points: the largest size (down to MIN_SIZE) at which each
        column holds its longest word whole; the room left goes first to the columns whose cells would
        otherwise wrap, then evenly. No word is ever cut inside a cell."""
        s = self.scale
        size = self.SIZE * s
        while True:
            words, lines = self._measure(size)
            if sum(words) <= aw or size <= self.MIN_SIZE * s:
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

    def _table(self, aw: float) -> Table:
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
        tab = Table(data, colWidths=widths)
        tab.setStyle(TableStyle(style))
        return tab

    def wrap(self, aw, ah):
        self._t = self._table(aw)
        self.width, self.height = self._t.wrap(aw, ah)
        return self.width, self.height

    def draw(self):
        self._t.drawOn(self.canv, 0, 0)


def learning_page(sheet: Sheet, text: str, scale: float = 1.0) -> list:
    """Reference text -> flowables: caption lines over tables, labels ("... :"), bullet lists, prose."""
    t = sheet.theme
    color = sheet.mark_color
    caption = sheet.style(13.5 * scale, font=t.heading, align=TA_CENTER, color=t.accent, leading=1.2)
    caption.spaceAfter = 6 * scale
    label = sheet.style(11.5 * scale, font=t.heading, align=TA_CENTER, leading=1.2)
    label.spaceAfter = 4 * scale
    prose = sheet.style(t.size * scale, align=TA_CENTER, leading=1.45)
    prose.spaceAfter = 8 * scale
    item = sheet.style(t.size * scale, align=TA_LEFT, leading=1.5)
    item.spaceAfter = 8 * scale

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
            out.append(TableBlock(sheet, rows, scale))
            continue
        if line.startswith(BULLET):
            items = []
            while k < len(lines) and lines[k].strip().startswith(BULLET):
                items.append(marked(lines[k].strip().lstrip("•-*– ").strip(), color))
                k += 1
            dot = f'<font color="{t.accent}">•</font>&nbsp;&nbsp;'
            out.append(Paragraph("<br/>".join(dot + x for x in items), item))
            continue
        nxt = next((lines[j] for j in range(k + 1, len(lines)) if lines[j].strip()), "")
        if is_table_line(nxt):
            out.append(Paragraph(marked(line, color), caption))
        elif line.endswith(":") and len(line) < 60:
            out.append(Paragraph(marked(line, color), label))
        else:
            out.append(Paragraph(marked(line, color), prose))
        k += 1
    return out
