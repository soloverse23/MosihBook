"""Claude as co-author: brief -> clarifying questions -> outline -> validated book.yaml.

Runs through the Claude Agent SDK, so it uses the Claude Code login on this machine, or
ANTHROPIC_API_KEY when one is set in Studio settings.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from . import characters, kdp, settings, spec, templates

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_DIR = {"picture_book": "picture-book", "storybook": "storybook", "comic": "comic"}
BOOK_TYPE = "storybook"  # the one format MosiBooks makes: a full-color illustrated learning storybook

RULES = """\
You are the co-author and art director of a print book that will be sold as an Amazon KDP paperback.
The book is produced by BookForge from a single book.yaml file: every illustration is generated from
`style` + the page `prompt` + character reference sheets, and all words are typeset separately.

Hard rules for book.yaml:
- Images never contain text. Prompts describe only visual content: no signs, labels, lettering,
  speech, quotes, logos, or "in the style of" any studio, franchise or living artist.
- Every prompt is concrete and visual (subject, action, setting, light, camera framing), 15-40 words,
  and leaves calm space where the text sits. At most 3 named characters per image.
- `style` is one rich paragraph of art direction (medium, palette, light, line, mood) reused for every image.
- Each character has a precise, fixed visual description (age, build, hair, clothing, colors) so it stays
  consistent across pages. Only use character names declared in `characters`.
- The book is always a full-color illustrated learning storybook: `type: storybook`, `paper: premium_color`.
  It mixes three kinds of pages, every one of them illustrated in color:
  - story pages that tell the story;
  - exercise pages ("Your turn!") right after the part of the story they practise: 1-3 short, clear tasks
    a child can do alone, tied to the book's learning goal;
  - learning-tip pages: one short, friendly explanation or rule with an example taken from the story.
  Every page is `illustration: opener` with a `prompt` (a full-page picture carrying that page's text). Set
  `chapter` on the first page of each chapter and on the first page of each exercise, tip or game section
  (its title is lettered on the picture too). Pages with no prompt only for long reference material
  (glossary, answer key, word lists): they are typeset inside a generated decorative frame.
- The book ENDS with a games section of 3-5 game pages. Be genuinely creative and varied, never a plain quiz:
  invent games that grow out of this story's world, characters and learning goal, for example an acting or
  mime game, a "draw what happens next" page, a make-your-own-ending, a treasure hunt back through the book's
  pages, a word or sound chain, a board-game path played with a coin or dice, a memory or riddle challenge
  between two players, a make-and-play craft. Each game page has a playful title, what you need (if
  anything) and 1-4 numbered steps a child can follow alone. The game must work from its words alone: the
  picture sets the scene or shows the characters playing it, but nothing may depend on exact drawn details
  (no mazes, spot-the-difference, counting or matching that relies on the image: the software makes
  those itself only through a book structure's maze and observation pages).
- Writing style: when the brief gives a writing style or an author to take inspiration from, write in that
  manner (rhythm, sentence length, rhyme, humour, kinds of images, how dialogue sounds) but never copy their
  sentences, characters, names or plots; everything stays original.
- Learning point and marking: when the brief has a learning point, weave it naturally into the story (never
  force irrelevant concepts to fill pages) and follow the writer's marking rule exactly in story pages: write
  every word the reader must see into `text` (e.g. the opposite in parentheses, if the rule says so), and wrap
  the part that is visually highlighted in [[double brackets]], e.g. "La mer est [[chaude (froide)]]." The
  brackets are never shown: the software colors that part. Copy the topic, explanation and marking rule into
  `learning` (topic, explain, marking). With a learning point but no marking rule, choose a simple, clear one.
- Book structure: when the brief gives a structure (numbered sections with page counts), the book has EXACTLY
  those pages, in that order: set `kind` on every page to its section's kind, and `chapter` on the first page
  of each section to its title (in the book's language). The structure replaces the free plan below (no
  extra games section, no dedication). Page kinds the software draws itself:
  - maze: write only the title (`chapter`) and a one-line instruction in `text`, and set
    `maze: {{start: <who sets off, a short visual description>, goal: <the destination, short visual>}}`.
    No `prompt`.
  - coloring: `prompt` describes a new scene for line art (never a story picture again); `text` is one short
    instruction, using the learning point where possible (e.g. "Colorie le grand château en rouge").
  - observation: `prompt` describes a rich scene; `text` is only the instruction ("Trouve dans l'image :");
    the list of things to find is made from the finished picture. Do not write one or its answers.
  - guided_drawing, imagination: `text` is the instruction; no `prompt` (the page is a big blank frame).
  - solutions, copyright: no `prompt`. Solutions answer every game with objectively checkable answers (not
    the comprehension questions, drawing pages, observation or the maze, which is added automatically).
  Other kinds are illustrated pages as described in the structure.
- trim must be one of: {trims}.
- Fill `cover_prompt`, `back_cover.blurb` (2-4 enticing sentences), and `front_matter.dedication`.
"""

QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "question": {"type": "string"},
                       "options": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "question"]}}},
    "required": ["questions"],
}

LISTING_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "categories": {"type": "array", "items": {"type": "string"}},
        "reading_age": {"type": "string"},
        "suggested_price_usd": {"type": "number"},
        "price_reasoning": {"type": "string"},
        "ai_disclosure": {"type": "string"},
    },
    "required": ["description", "keywords", "categories", "reading_age", "ai_disclosure"],
}


class AuthorError(RuntimeError):
    pass


def _system(book_type: str) -> str:
    parts = [RULES.format(trims=", ".join(sorted(kdp.TRIMS)))]
    if lib := characters.library():
        parts.append("Characters already drawn for earlier books (the writer's character library). When this "
                     "book uses one of them (a series, a returning hero), use exactly this name and copy the "
                     "description word for word, so the locked artwork is reused:\n" +
                     "\n".join(f"- {c['name']} (from {c.get('source_book', '?')}): {c['description']}" for c in lib))
    example = EXAMPLES / EXAMPLE_DIR.get(book_type, "picture-book") / "book.yaml"
    if example.exists():
        parts.append(f"A complete, valid example of a {book_type} book.yaml, for its structure only (this book is "
                     f"full color, with exercises, tips and games):\n```yaml\n{example.read_text()}```")
    return "\n\n".join(parts)


NESTED = {
    "learning": ("Learning point", {"topic": "topic", "targets": "target words or concepts",
                                    "explain": "what the child should understand",
                                    "marking": "marking rule (how the learning words appear in the story)"}),
    "writing": ("Writing style", {"inspired_by": "take inspiration from (style only, never copy)",
                                  "notes": "style notes", "sample": "sample of the wanted style"}),
}


def _empty(v) -> bool:
    return v in (None, "", [], {}) or (isinstance(v, dict) and all(_empty(x) for x in v.values()))


def structure(brief: dict) -> list[dict]:
    """The brief's active book structure: [{kind, pages, title, note}], or [] for a free plan."""
    st = brief.get("structure") or {}
    return [x for x in (st.get("sections") or []) if x.get("enabled", True) and int(x.get("pages") or 0) > 0]


def _brief_text(brief: dict) -> str:
    lines = [f"- {k}: {v}" for k, v in brief.items()
             if not _empty(v) and k not in ("cast", "page_numbers", "type", "paper", "structure", *NESTED)]
    for key, (label, fields) in NESTED.items():
        if not _empty(sub := brief.get(key) or {}):
            lines.append(f"- {label}:")
            lines += [f"  - {name}: {sub[f]}" for f, name in fields.items() if not _empty(sub.get(f))]
    st = brief.get("structure") or {}
    if secs := structure(brief):
        lines.append("- Book structure (follow exactly):\n" + templates.structure_text(secs, st.get("back_cover")))
    if not _empty(st.get("collection")):
        lines.append(f"- Other books in this collection (use only these, as stated): {st['collection']}")
    if cast := brief.get("cast"):  # characters picked from the library: reuse them exactly
        known = {c["name"]: c for c in characters.library()}
        lines.append("- cast from the character library (must appear; use exactly these names and copy the "
                     "descriptions word for word):")
        lines += [f"  - {n}: {known[n]['description']}" for n in cast if n in known]
    return "\n".join(lines)


def _refs(refs: str) -> str:
    return (f"\n\nReference material the writer attached (use it as source and inspiration; the brief wins "
            f"where they disagree; attached images are shown to you as pictures):\n<attachments>\n{refs}\n</attachments>") if refs else ""


def _answers_text(questions: list[dict], answers: dict) -> str:
    return "\n".join(f"- {q['question']}\n  answer: {answers.get(q['id'], '(no answer - use your judgment)')}"
                     for q in questions)


def _image_block(path: Path) -> dict:
    """An image as a Claude content block, shrunk to fit the API limits (8000 px, 5 MB)."""
    import base64
    import io
    from PIL import Image
    img = Image.open(path)
    img.thumbnail((1568, 1568))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buf.getvalue()).decode()}}


def _with_images(prompt: str, images):
    """Streaming-input prompt: the attached images, then the text, as one user message."""
    content = [b for p in images for b in ({"type": "text", "text": f"Attached image: {Path(p).name}"},
                                           _image_block(Path(p)))]

    async def gen():
        yield {"type": "user", "message": {"role": "user", "content": content + [{"type": "text", "text": prompt}]},
               "parent_tool_use_id": None, "session_id": "default"}
    return gen()


async def ask(prompt: str, system: str, schema: dict | None = None, images=()):
    """One Claude turn with no tools. Returns text, or the parsed object when `schema` is given.
    `images` are local image files shown to Claude with the prompt."""
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

    s = settings.load()
    s.apply_env()
    options = ClaudeAgentOptions(
        system_prompt=system, model=s.claude_model, tools=[], setting_sources=[],
        max_turns=3 if schema else 1,
        output_format={"type": "json_schema", "schema": schema} if schema else None,
    )
    text, result = [], None
    try:
        async for msg in query(prompt=_with_images(prompt, images) if images else prompt, options=options):
            if isinstance(msg, AssistantMessage):
                text += [b.text for b in msg.content if isinstance(b, TextBlock)]
            elif isinstance(msg, ResultMessage):
                result = msg
    except Exception as e:  # CLI missing, not logged in, network
        raise AuthorError(f"Claude call failed: {e}. Check Settings > Claude (log in with `claude` "
                          "in a terminal, or add an Anthropic API key).") from e
    if result is None or result.is_error:
        raise AuthorError(f"Claude returned an error: {(result.errors if result else None) or result.result}")
    if schema:
        if result.structured_output is not None:
            return result.structured_output
        return json.loads(_fenced(result.result or "".join(text), "json"))
    return result.result or "\n".join(text)


def _fenced(text: str, lang: str) -> str:
    m = re.search(rf"```(?:{lang})?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


async def questions(brief: dict, refs: str = "", images=()) -> list[dict]:
    out = await ask(
        f"A writer wants this book:\n{_brief_text(brief)}{_refs(refs)}\n\nAsk 3-6 short clarifying questions that would most "
        "change the story or the art (main character, what children should learn, emotional arc, setting, art style, "
        "ending, length...). "
        "Skip anything the brief or the attachments already answer. If the brief has a learning point but no rule for "
        "marking it in the text, ask how to mark it (suggest options). Give 2-4 concrete suggested options per question.",
        _system(BOOK_TYPE), QUESTIONS_SCHEMA, images)
    return out["questions"]


async def outline(brief: dict, qs: list[dict], answers: dict, feedback: str = "", previous: str = "",
                  refs: str = "", images=()) -> str:
    prompt = (f"Brief:\n{_brief_text(brief)}{_refs(refs)}\n\nClarifications:\n{_answers_text(qs, answers)}\n\n"
              "Write a book outline in Markdown with these sections: ## Title (3 options, the first is your pick), "
              "## Logline, ## Characters (with fixed visual descriptions), ## Art style, ## Format "
              "(trim, page count and why), ## Page plan (numbered pages, one line each, marked [story], [exercise], "
              "[tip] or [game], with the illustration idea; the games section comes last). When the brief gives a "
              "book structure, the page plan follows it exactly and marks each page with its section kind instead, "
              "e.g. [story], [coloring], [maze]. Output only the outline.")
    if previous:
        prompt += f"\n\nPrevious outline:\n{previous}\n\nRevise it with this feedback: {feedback}"
    return await ask(prompt, _system(BOOK_TYPE), images=images)


async def write_book(brief: dict, outline_md: str, image_block: dict, refs: str = "", images=()) -> str:
    prompt = (f"Brief:\n{_brief_text(brief)}{_refs(refs)}\n\nApproved outline:\n{outline_md}\n\n"
              f"Write the complete book.yaml for this outline. Use author: {brief.get('author') or 'Your Name'}. "
              "Write the full final text of every page (not placeholders). "
              "Output only the YAML in one ```yaml block.")
    fixed = {"type": BOOK_TYPE, "paper": "premium_color", "page_numbers": bool(brief.get("page_numbers", True))}
    if secs := structure(brief):
        fixed["sections"] = secs
    if brief.get("language"):
        fixed["language"] = brief["language"]
    learning = {k: brief["learning"][k] for k in ("topic", "explain", "marking")
                if not _empty((brief.get("learning") or {}).get(k))}
    return await _validated(prompt, BOOK_TYPE, image_block, images, fixed, learning)


async def revise(book_yaml: str, instruction: str) -> str:
    book_type = (yaml.safe_load(book_yaml) or {}).get("type", "picture_book")
    images = (yaml.safe_load(book_yaml) or {}).get("images", {})
    prompt = (f"Current book.yaml:\n```yaml\n{book_yaml}```\n\nApply this change: {instruction}\n"
              "Keep everything else as it is. Output the complete updated YAML in one ```yaml block.")
    return await _validated(prompt, book_type, images)


def structure_errors(data: dict) -> list[str]:
    """Where a template book's pages differ from its structure (section kinds and page counts, in order)."""
    want = [s["kind"] for s in data.get("sections") or [] for _ in range(int(s.get("pages", 1)))]
    if not want:
        return []
    got = [(pg or {}).get("kind") for pg in data.get("pages") or []]
    if got == want:
        return []
    errs = [f"the structure has {len(want)} pages, the book has {len(got)}"] if len(got) != len(want) else []
    errs += [f"page {i}: kind should be {w!r}, is {g!r}" for i, (w, g) in enumerate(zip(want, got), 1) if w != g][:8]
    return errs


async def _validated(prompt: str, book_type: str, image_block: dict, images=(), fixed: dict | None = None,
                     learning: dict | None = None) -> str:
    system = _system(book_type)
    text = _fenced(await ask(prompt, system, images=images), "yaml")
    for attempt in range(2):
        try:
            data = yaml.safe_load(text)
            data["images"] = {**(data.get("images") or {}), **image_block}
            data.update(fixed or {})
            if learning:  # the writer's own words win over Claude's copy
                data["learning"] = {**(data.get("learning") or {}), **learning}
            if errs := structure_errors(data):
                raise ValueError("the pages do not follow the book structure: " + "; ".join(errs))
            spec.Book.model_validate(data)
            return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
        except (ValidationError, ValueError, yaml.YAMLError, TypeError, AttributeError) as e:
            if attempt == 1:
                raise AuthorError(f"Claude's book.yaml did not validate: {e}") from e
            text = _fenced(await ask(
                f"{prompt}\n\nYour previous answer:\n```yaml\n{text}```\nfailed validation:\n{e}\n"
                "Fix it and output the complete YAML in one ```yaml block.", system), "yaml")
    raise AssertionError("unreachable")


async def listing(book_yaml: str, pages: int | None) -> dict:
    return await ask(
        f"Here is a finished book:\n```yaml\n{book_yaml}```\nInterior page count: {pages or 'unknown'}.\n\n"
        "Draft its Amazon KDP paperback listing: a description (150-300 words, simple HTML allowed: <b>, <i>, <br>), "
        "exactly 7 search keyword phrases (no title words, no brand names), 2-3 browse categories as full paths, "
        "a reading age range, a suggested USD list price with reasoning based on genre norms and print cost, "
        "and a one-sentence note on what to declare in KDP's AI-generated content question (images are AI-generated; "
        "say whether text is AI-generated or AI-assisted based on how it was written with you).",
        _system(yaml.safe_load(book_yaml).get("type", "picture_book")), LISTING_SCHEMA)


async def ping() -> str:
    return (await ask("Reply with the single word: ok", "You are a connectivity check.")).strip()
