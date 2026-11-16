"""Offline provider: deterministic painted-landscape placeholders so the pipeline runs for free
and layouts can be judged with something that reads like real art."""
from __future__ import annotations

import colorsys
import hashlib
import io
import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .openai_images import flex_size

WORK_W = 900  # paint small, then resample to the requested size
FONT = Path(__file__).resolve().parent.parent / "fonts" / "Andika-Bold.ttf"
LETTER_BLOCK = re.compile(r"<<<\n(.*?)\n>>>", re.S)


def _hsv(h: float, s: float, v: float) -> tuple[int, int, int]:
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1, s, v))


class MockProvider:
    name = "mock"
    model = "mock"

    def __init__(self, max_pixels: int):
        self.max_pixels = max_pixels

    def request_size(self, aspect: float) -> tuple[int, int]:
        return flex_size(aspect, self.max_pixels)  # same sizing rules as gpt-image-2

    def generate(self, prompt: str, size: tuple[int, int], refs: list[Path], quality: str | None = None) -> bytes:
        rnd = random.Random(hashlib.sha256(prompt.encode()).digest())
        w, h = WORK_W, max(1, round(WORK_W * size[1] / size[0]))
        night = rnd.random() < 0.5
        hue = rnd.random()
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)

        # sky
        top = _hsv(hue, 0.55, 0.32 if night else 0.85)
        bottom = _hsv(hue + 0.08, 0.35, 0.55 if night else 0.98)
        for y in range(h):
            t = y / h
            draw.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
        if night:
            for _ in range(160):
                x, y, r = rnd.random() * w, rnd.random() * h * 0.6, rnd.choice((1, 1, 1.5, 2))
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 225))

        # sun or moon with a soft glow
        cx, cy, r = w * rnd.uniform(0.2, 0.8), h * rnd.uniform(0.15, 0.35), min(w, h) * rnd.uniform(0.06, 0.1)
        glow = Image.new("L", (w, h), 0)
        ImageDraw.Draw(glow).ellipse([cx - r * 3, cy - r * 3, cx + r * 3, cy + r * 3], fill=140)
        glow = glow.filter(ImageFilter.GaussianBlur(r * 1.2))
        img.paste((255, 240, 200), mask=glow)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 246, 214) if night else (255, 214, 140))

        # layered hills, far to near
        land = hue + rnd.choice((0.25, 0.33, 0.45))
        for k, layer in enumerate(range(4)):
            base = h * (0.55 + 0.11 * layer)
            amp, freq, phase = h * rnd.uniform(0.03, 0.08), rnd.uniform(1.0, 2.6), rnd.uniform(0, 6.3)
            pts = [(x, base - amp * math.sin(x / w * freq * math.pi * 2 + phase)) for x in range(0, w + 10, 10)]
            v = (0.3 + 0.1 * layer) if night else (0.75 - 0.12 * layer)
            draw.polygon(pts + [(w, h), (0, h)], fill=_hsv(land + 0.03 * layer, 0.45 + 0.08 * layer, v))
            for _ in range(rnd.randint(0, 3) if layer == 2 else 0):  # a few trees on the mid hill
                tx = rnd.random() * w
                ty = base - amp * math.sin(tx / w * freq * math.pi * 2 + phase)
                th = h * rnd.uniform(0.07, 0.13)
                draw.polygon([(tx, ty - th), (tx - th * 0.3, ty + 2), (tx + th * 0.3, ty + 2)],
                             fill=_hsv(land + 0.05, 0.6, v * 0.7))

        # painterly softness + paper grain
        img = img.filter(ImageFilter.GaussianBlur(1.2))
        grain = Image.frombytes("L", (w, h), rnd.randbytes(w * h)).filter(ImageFilter.BoxBlur(1)).convert("RGB")
        img = Image.blend(img, grain, 0.06)
        img = img.resize(size, Image.BICUBIC)
        if "Decorative page frame" in prompt:  # the empty centre the text pages are typeset into
            ImageDraw.Draw(img).rectangle([size[0] * 0.12, size[1] * 0.10, size[0] * 0.88, size[1] * 0.90],
                                          fill=(255, 252, 245))
        if "TEXT TO LETTER" in prompt:
            _letter(img, prompt)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()


def _letter(img: Image.Image, prompt: str) -> None:
    """Stand-in for the image model's lettering: the exact words, wrapped and centered where asked."""
    block = prompt[prompt.index("TEXT TO LETTER"):]
    texts = LETTER_BLOCK.findall(block)
    if not texts:
        return
    w, h = img.size
    x0, span = 0, w
    if "the book's fold" in prompt:  # a spread: letter on the left page, clear of the fold
        x0, span = w * 0.04, w * 0.42
    heading = texts[0] if len(texts) > 1 else None
    body = texts[-1]
    draw = ImageDraw.Draw(img)
    lines: list[tuple[str, ImageFont.FreeTypeFont]] = []

    def wrap(text: str, font: ImageFont.FreeTypeFont) -> None:
        for para in text.splitlines():
            cur = ""
            for word in para.split():
                trial = f"{cur} {word}".strip()
                if draw.textlength(trial, font=font) > span * 0.82 and cur:
                    lines.append((cur, font))
                    cur = word
                else:
                    cur = trial
            lines.append((cur, font))

    body_font = ImageFont.truetype(str(FONT), max(10, round(h * 0.035)))
    if heading:
        wrap(heading, ImageFont.truetype(str(FONT), max(14, round(h * 0.06))))
    wrap(body, body_font)
    heights = [f.size * 1.3 for _, f in lines]
    total = sum(heights)
    place = block.split("Place the words ", 1)[-1]
    y = h * 0.08 if place.startswith(("in the upper", "in the upper two-thirds")) else h * 0.92 - total
    for (line, font), lh in zip(lines, heights):
        x = x0 + (span - draw.textlength(line, font=font)) / 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 250, 235))
        y += lh
