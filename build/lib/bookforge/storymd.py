"""story.md -> book.yaml.

Format: a YAML header (everything before the first `---` line), then pages separated by `---`.
Inside a page, lines starting with `> key: value` set page fields (prompt, layout, chapter, ...);
everything else is the page text.
"""
from __future__ import annotations

import yaml

TEMPLATE = """\
title: My Book
author: Your Name
type: picture_book        # picture_book | storybook | comic
trim: 8.5x8.5             # any KDP trim, e.g. 8x10, 6x9
paper: premium_color
style: >
  Soft watercolor and gouache children's book illustration, warm golden light,
  gentle textures, expressive characters.
lettering: rounded, friendly hand-lettered serif in warm dark ink, generous spacing
characters:
  - name: Mia
    description: a 6-year-old girl with curly black hair, yellow raincoat, red boots
cover_prompt: Mia standing on a hill under a giant glowing moon
back_cover:
  blurb: One rainy night, Mia finds a door in the moonlight...
pages:
  - text: One rainy night, Mia couldn't sleep.
    prompt: Mia looking out of her bedroom window at the rain, cozy lamp light
    layout: full_bleed
images:
  text_in_art: true          # the words are lettered into each illustration
"""


def convert(md: str) -> str:
    header, *chunks = md.split("\n---\n")
    book = yaml.safe_load(header) or {}
    pages = []
    for chunk in chunks:
        page, text = {}, []
        for line in chunk.strip().splitlines():
            if line.startswith(">") and ":" in line:
                key, value = line[1:].split(":", 1)
                page[key.strip()] = value.strip()
            else:
                text.append(line)
        page["text"] = "\n".join(text).strip()
        pages.append(page)
    book["pages"] = pages
    return yaml.safe_dump(book, sort_keys=False, allow_unicode=True, width=100)
