# BookForge

Story + illustration prompts in → Amazon KDP print-ready `interior.pdf` + `cover.pdf` out.
Picture books, illustrated storybooks and comics.

```
book.yaml → plan → character sheets → page art → fit/upscale to 300 DPI → layout → cover → preflight
```

## Setup

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
export OPENAI_API_KEY=sk-...
```

**Recommended: the Real-ESRGAN AI upscaler.** Art is generated at up to 2560×1440 (the largest size OpenAI
doesn't call experimental), so a full-bleed 8.5" page needs about 2× upscaling. Without Real-ESRGAN that is
done by plain resizing, which prints visibly softer. Unzip the macOS release
(`realesrgan-ncnn-vulkan-20220424-macos.zip` from https://github.com/xinntao/Real-ESRGAN/releases) into
`tools/realesrgan/`. BookForge finds it there, on `PATH`, or at `BOOKFORGE_REALESRGAN`.

## Use

```bash
bookforge init  my-book/book.yaml            # starter template (or: --from story.md)
bookforge plan  my-book/book.yaml            # images needed, cost estimate, prompt check
bookforge all   my-book/book.yaml --mock     # free dry run with placeholder art
bookforge pilot my-book/book.yaml            # characters + cover + 3 pages: approve the look first
bookforge all   my-book/book.yaml            # everything, each image reviewed (cached: never pays twice)
bookforge regen my-book/book.yaml p007 --note "Pip smaller, facing the lantern"
open my-book/build/review.html               # every image: score, issues, prompt, regen command
open my-book/build/preview.html              # the finished book as two-page spreads
```

## Image quality

How BookForge gets good, consistent images from your prompts:

1. **Prompt check before spending.** `plan`, `pilot` and `art` flag prompts that ask for words in the image
   (AI lettering comes out garbled), name a studio or artist style (blocked: copyright and KDP risk), are too
   vague, crowd more than 3 recurring characters into one scene, or leave a spread's subject in the fold.
2. **Structured prompts.** Every image gets the same labeled structure: style, palette, scene, characters
   (descriptions repeated word for word), composition rules from its print layout (calm space where text
   goes, subjects away from trimmed edges and the fold), and hard rules (no text, no collage, correct anatomy).
3. **Reference images, labeled.** Character sheets are generated first. The cover is generated next and
   becomes the style anchor. Every page attaches the sheets of the characters in it plus the cover, and the
   prompt says what each attached image is for ("Image 1: character reference for Pip…").
4. **Automatic art review.** A vision model (`review_model`, default `gpt-5-mini`) checks each image against the
   references for visible text, character drift, duplicates, anatomy errors, composition and style. It only flags
   problems: every image is generated once, and nothing is ever redrawn unless you ask (Redo / `bookforge regen`
   with a note). "Generate all art" only draws missing images; a page whose prompt changed after it was drawn is
   flagged for a Redo instead of being re-bought.
5. **Pilot first.** `bookforge pilot` produces only the character sheets, cover and first pages, so you can
   fix the style or descriptions before paying for the whole book.

Tune these in `book.yaml` under `images:` (`model`, `quality`: up to `xhigh`/`max`, `max_pixels`,
`style_anchor`, `review`, `min_score`). `page_numbers: false` in book.yaml leaves the page numbers out.

Upload `build/interior.pdf` and `build/cover.pdf` to KDP. Choose "Bleed" and the same trim and paper as in
`book.yaml`, check the KDP Print Previewer, and order a proof copy before publishing. KDP asks you to
disclose AI-generated images during setup.

## MosiBooks (web UI)

```bash
uv pip install -e ".[web]"
mosibooks serve                     # http://127.0.0.1:8765 (same as `bookforge serve`)
```

A local web app that walks you through a book step by step: **brief → Claude's questions → outline → manuscript
(book.yaml) → free mock preview → pilot / full art with review → build + preflight → download + Amazon listing**.
It also has a publishing guide with a KDP royalty calculator.

- Claude runs through the Claude Agent SDK on the Claude Code login of this machine (run `claude` once to log
  in). Or paste an Anthropic API key in Settings to pay per token instead.
- Keys and defaults live in `~/.bookforge/settings.json` (mode 600). The API only returns keys masked.
- Books are saved to `books/<slug>/book.yaml`, so every CLI command above works on them too.
- Book fonts are Latin-only for now, so non-Latin text (e.g. Persian) won't typeset yet.

## book.yaml

See `examples/` for one of each type. Key fields:

| field | meaning |
|---|---|
| `type` | `picture_book`, `storybook`, `comic` |
| `trim`, `paper` | KDP trim (e.g. `8.5x8.5`, `6x9`) and paper (`premium_color`, `cream_bw`, …) |
| `style` | art direction added to every prompt; the main lever for a consistent look |
| `lettering` | lettering direction for words drawn into the art (`text_in_art`): letterform, ink, weight |
| `characters` | name + visual description (+ optional `reference` image). A reference sheet is generated first and attached to every illustration that mentions the character. |
| `pages[].layout` | picture book: `full_bleed`, `split`, `spread`, `spot`, `text_only` |
| `pages[].chapter`, `illustration` | storybook: chapter title; `opener` (full-page art with the page's text printed on it, in the calm area set by `text_position`) or `spot` art |
| `pages[].panels[].bubbles` | comic: 1–6 panels; `speech`, `thought`, `caption` balloons |

**Words in the pictures (`images.text_in_art: true`, the default for new books).** The image model letters each
page's exact text into its illustration in one lettering style for the whole book (`lettering:` in book.yaml, plus the
cover as lettering reference). The cover carries the title, subtitle and author, and the back cover the blurb, with
an empty corner for the barcode. The art review reads every word and compares it with the page text, and a
misspelled image is marked red in
`review.html`, and preflight refuses to pass until it is redone (`bookforge regen book.yaml p004`). Long
text-only pages (glossaries, word lists) are typeset in the book font inside a generated decorative frame, and
the copyright page is always typeset. Latin script only: image models can't letter Persian or Arabic reliably.

With `text_in_art: false` (older books), images contain no text: words are typeset on a soft panel over the art.

## Characters

The first time a character's sheet is drawn it is locked in `characters/<name>/` next to `book.yaml`
(`sheet.png` + `character.yaml` with the exact description). Every later run, and every page, uses that sheet and
wording, so the look never drifts. Each locked character is also copied to the shared library
`~/.bookforge/characters/`, and a new book that declares a character with the same name starts from it (a series).

```bash
bookforge characters list  my-book/book.yaml            # what is locked, and the library
bookforge characters reset my-book/book.yaml "Pip"      # redraw Pip on the next art run
```

In MosiBooks the **Characters** page shows the whole library: replace a character's image with your own, or remove it.
A new book's brief lets you tick library characters, and Claude writes them in with their exact descriptions.

## What preflight checks

Page size including bleed, an even page count of at least 24, the gutter for the page count, embedded fonts, text inside
the safe area, art resolution before upscaling, runs of blank pages, cover width from the real spine, the clear
barcode area, and spine text only at 80+ pages.

## Learning point, writing style and book structure (all optional, in the brief)

- **Learning point**: what the book teaches, target words, what the child should understand, and *your* rule
  for marking it in the story (e.g. "the adjective in violet, its opposite in parentheses after it"). Claude
  writes every visible word into the page text and wraps the highlighted part in `[[...]]`; the image model
  letters it in the highlight style, typeset pages print it in `learning.color` (violet by default).
- **Writing style**: an author to take inspiration from, style notes, a sample passage. Style only; nothing copied.
- **Book structure**: pick a template (Templates page; built-in: *Anahita Darius - 40 pages*), then switch
  sections on/off, change page counts, titles and notes for this book. "Save as template" stores it in
  `~/.bookforge/templates/`. A structured book has exactly those pages (`kind` on every page, checked when
  Claude writes it) and no built-in title/copyright/dedication pages.
- Pages the software draws itself: **maze** (generated in code, always solvable; its answer is added to the
  solutions page), **guided drawing / imagination** (big blank frame), **coloring** (black-and-white line art,
  instruction typeset above), **observation** (the find-list is read from the finished picture by the vision
  model, so everything on it is really there).
