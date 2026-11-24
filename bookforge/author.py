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

from . import characters, kdp, settings, spec, templates, words

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
  (glossary, answer key, word lists): they are typeset inside a generated decorative frame. A `reference`
  page with no prompt gets its own border drawn from its examples, and its words are typeset exactly:
  a caption line, then a table as `| | col | col |` rows, then a label ending in ":" and `•` examples.
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
  - matching: `text` is the one-line instruction; set `matching: {{pairs: [[left, right], ...]}}` with 4-6
    pairs written in their correct pairing (the software shuffles the right column). Every left item and every
    right item different, so exactly one pairing is correct.
  - fill_in and main_game: `text` is the instruction; set `fill_in: {{items: [{{prompt, answer}}, ...]}}` with
    3-8 items. Put "___" in `prompt` where the child writes; an item without "___" gets a writing line under it.
    Every `answer` is short and the only correct one.
  - odd_one_out: `text` is the instruction; set `odd_one_out: {{groups: [{{items: [...], answer}}, ...]}}`, 3-5
    groups of 4 words or numbers, `answer` being exactly one of that group's items, the only one that does not
    belong, for a reason a child of the book's age can say.
  - final_challenge: `text` is the challenge (short); set `certificate: {{title, name_label, date_label}}` in
    the book's language (e.g. "Bravo !", "Prénom", "Date").
  - On matching, fill_in, main_game and odd_one_out pages `prompt` is optional: a small vignette of a character
    or object, never the game itself (the software lays the game out). On final_challenge: no `prompt`.
  - solutions, copyright: no `prompt`. The software prints the answers of the maze, matching, fill_in,
    main_game and odd_one_out pages itself: the solutions `text` is only a short line introducing them, plus
    answers to any other game with objectively checkable answers (never the comprehension questions, drawing
    pages or observation).
  Other kinds are illustrated pages as described in the structure.
- Language: `language` is the book's language ({languages}). Every word a reader sees is written in it, natively
  and with its own typography (an ellipsis always 3 dots, never 4; accents and diacritics always, e.g. Romanian ș ț with a comma below; French
  « guillemets » and the curly apostrophe ’ (l’été, qu’il, aujourd’hui); German „Anführungszeichen“; Spanish ¡ ¿): title, subtitle, page `text`, `chapter` titles,
  exercise and game headings (never an English "Your turn!" in a French book), game data, certificate, blurb,
  dedication, about_author, copyright. Image `prompt`s, `style`, `lettering` and character descriptions stay
  in English. Character names stay as the brief gives them.
- trim must be one of: {trims}.
- Fill `cover_prompt`, `back_cover.blurb` (2-4 enticing sentences), and `front_matter.dedication`.
"""

QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "question": {"type": "string"},
                       "why": {"type": "string", "description": "a few words on what the answer changes in the book"},
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
        "ai_disclosure": {"type": "string"},
    },
    "required": ["description", "keywords", "categories", "reading_age", "ai_disclosure"],
}


class AuthorError(RuntimeError):
    pass


def _system(book_type: str) -> str:
    parts = [RULES.format(trims=", ".join(sorted(kdp.TRIMS)), languages=", ".join(words.LANGUAGES))]
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


async def _ask_api(key: str, model: str, prompt: str, system: str, schema: dict | None, images, on_text=None) -> str:
    """One turn on the Claude API with this studio's (or account's) own key. Streams, because a whole
    book.yaml is a long answer."""
    import anthropic
    if schema:
        prompt += ("\n\nReply with only a JSON object (in one ```json block) that matches this JSON schema:\n"
                   + json.dumps(schema))
    content = [b for p in images for b in ({"type": "text", "text": f"Attached image: {Path(p).name}"},
                                           _image_block(Path(p)))] + [{"type": "text", "text": prompt}]
    client = anthropic.AsyncAnthropic(api_key=key)
    req = dict(model=model, max_tokens=64000, system=system, output_config={"effort": "high"},
               messages=[{"role": "user", "content": content}])
    try:
        try:  # on a safety decline the API retries on a fallback model in the same call
            async with client.beta.messages.stream(**req, betas=["server-side-fallback-2026-07-01"],
                                                   fallbacks="default") as stream:
                msg = await _follow(stream, on_text)
        except anthropic.BadRequestError as e:
            if "fallback" not in str(e).lower():
                raise
            async with client.messages.stream(**req) as stream:  # account without the fallback beta
                msg = await _follow(stream, on_text)
    except anthropic.AuthenticationError as e:
        raise AuthorError("Anthropic rejected the API key. Check it in Settings > Claude.") from e
    except anthropic.PermissionDeniedError as e:
        raise AuthorError(f"This Anthropic key can't use {model}: {e.message}") from e
    except anthropic.RateLimitError as e:
        raise AuthorError("Anthropic rate limit or credit limit reached; try again in a minute "
                          "or add credit at console.anthropic.com.") from e
    except anthropic.APIStatusError as e:
        raise AuthorError(f"Claude API error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AuthorError("Couldn't reach the Claude API (network).") from e
    if msg.stop_reason == "refusal":
        raise AuthorError("Claude declined this request. Rephrase the brief and try again.")
    if msg.stop_reason == "max_tokens":
        raise AuthorError("Claude's answer was cut off (too long). Shorten the book or the request.")
    return "".join(b.text for b in msg.content if b.type == "text")


async def _follow(stream, on_text):
    """The final message of an API stream; `on_text(text so far)` sees the answer grow as it is written."""
    if on_text:
        acc = ""
        async for piece in stream.text_stream:
            acc += piece
            on_text(acc)
    return await stream.get_final_message()


async def ask(prompt: str, system: str, schema: dict | None = None, images=(), on_text=None):
    """One Claude turn with no tools. Returns text, or the parsed object when `schema` is given.
    `images` are local image files shown to Claude with the prompt. `on_text(text so far)` is called while the
    answer is written (a long translation shows how far it got).

    With an Anthropic API key (always the case for accounts on a server) it calls the Claude API
    directly; otherwise it runs on the Claude Code login of this computer (claude-agent-sdk)."""
    s = settings.load()
    if s.anthropic_api_key:
        text = await _ask_api(s.anthropic_api_key, s.claude_model, prompt, system, schema, images, on_text)
        return json.loads(_fenced(text, "json")) if schema else text
    if settings.current_user.get():
        raise AuthorError("Connect Claude first: add your Anthropic API key in Settings > Claude.")
    try:
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, StreamEvent, TextBlock, query
    except ImportError as e:
        raise AuthorError("Claude isn't available on this server (claude-agent-sdk is not installed; it is left "
                          "out of the Vercel build). Run MosiBooks on your own computer to write books with Claude.") from e

    s = settings.load()
    s.apply_env()
    options = ClaudeAgentOptions(
        system_prompt=system, model=s.claude_model, tools=[], setting_sources=[],
        max_turns=3 if schema else 1,
        output_format={"type": "json_schema", "schema": schema} if schema else None,
        include_partial_messages=bool(on_text),
    )
    text, result, partial = [], None, ""
    try:
        async for msg in query(prompt=_with_images(prompt, images) if images else prompt, options=options):
            if isinstance(msg, StreamEvent):
                # the answer as it is written: plain text, or the structured output's JSON
                delta = (msg.event or {}).get("delta") or {}
                piece = delta.get("text") or delta.get("partial_json") or ""
                if piece and on_text:
                    partial += piece
                    on_text(partial)
            elif isinstance(msg, AssistantMessage):
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
        "Ask only about what the brief and the attachments leave open: never re-ask something they already say, even in "
        "other words, and never ask about the book structure, page count, trim or title when the brief sets them. "
        "Each question covers one thing; put what the answer changes in the book in `why`. A question about the art "
        "style must have the id `art_style` (the app shows it as a gallery of style pictures). If the brief has a learning point but no rule for "
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
              "e.g. [story], [coloring], [maze]. Write the title options and every page's words in the book's "
              f"language ({words.canonical(brief.get('language')) or 'English'}); the rest of the outline in the "
              "language the brief is written in. Output only the outline.")
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
        fixed["language"] = words.canonical(brief["language"]) or brief["language"]
    learning = {k: brief["learning"][k] for k in ("topic", "explain", "marking")
                if not _empty((brief.get("learning") or {}).get(k))}
    return await _validated(prompt, BOOK_TYPE, image_block, images, fixed, learning)


KEPT = ("type", "paper", "language", "page_numbers", "sections", "images")  # never changed by an edit

EDIT_FORMAT = """\
Answer with only the parts that change, in one ```yaml block, in this shape (leave out every key you do not need):
```yaml
pages:          # pages that change, by their number (the "# page N" marks); each one written out complete
  5:
    text: ...
    prompt: ...
delete: [7]     # pages to remove, by their number
insert:         # new pages: `after` is the number of the page they follow (0 = at the very start)
  - after: 3
    page: {text: ..., prompt: ...}
book:           # fields outside `pages` that change (title, style, characters, back_cover, front_matter,
  title: ...    # cover_prompt, ...), each written out complete
```
Page numbers always mean the numbers in the "# page N" marks of the book as it is now. A page you list under
`pages` replaces that page entirely: copy every field you do not change word for word. Never list a page or a
field the change does not touch. Only when the book truly already does what is asked, answer with just
`note:` and one sentence, in the language the request is written in, saying why nothing needs to change."""


def numbered(data: dict) -> str:
    """book.yaml with a "# page N" mark before every page, so a request about page 12 lands on page 12."""
    head = {k: v for k, v in data.items() if k not in ("pages", "images")}
    out = [yaml.safe_dump(head, sort_keys=False, allow_unicode=True, width=100).rstrip(), "pages:"]
    for n, pg in enumerate(data.get("pages") or [], 1):
        body = yaml.safe_dump([pg], sort_keys=False, allow_unicode=True, width=100).rstrip()
        out += [f"# page {n}", body]
    return "\n".join(out) + "\n"


def apply_patch(data: dict, patch: dict) -> dict:
    """The book with Claude's changes spliced in. Pages and fields the patch does not name stay exactly
    as they were."""
    if not isinstance(patch, dict):
        raise ValueError("the answer is not a list of changes")
    pages = list(data.get("pages") or [])
    n = len(pages)
    patch = dict(patch)
    book = dict(patch.get("book") or {})
    if "pages" in book and "pages" not in patch:      # pages put under `book:` by mistake
        patch["pages"] = book.pop("pages")
    patch["book"] = book
    if isinstance(patch.get("pages"), list):          # the whole page list sent back: keep it page by page
        full = patch["pages"]
        if len(full) != n:
            raise ValueError(f"the answer lists {len(full)} pages, the book has {n}: send only the pages that change, by number")
        patch["pages"] = {i: pg for i, pg in enumerate(full, 1) if pg != pages[i - 1]}

    def num(k) -> int:
        try:
            k = int(k)
        except (TypeError, ValueError):
            raise ValueError(f"{k!r} is not a page number")
        return k

    for k, pg in (patch.get("pages") or {}).items():
        if not 1 <= num(k) <= n or not isinstance(pg, dict):
            raise ValueError(f"page {k}: there is no such page (the book has {n}), or it is not written out")
        pages[num(k) - 1] = pg
    gone = {num(k) for k in (patch.get("delete") or [])}
    if any(not 1 <= k <= n for k in gone):
        raise ValueError(f"delete: the book has pages 1 to {n}")
    after: dict[int, list] = {}
    for ins in patch.get("insert") or []:
        a = num((ins or {}).get("after", n))
        if not 0 <= a <= n or not isinstance(ins.get("page"), dict):
            raise ValueError(f"insert after {a}: there is no such page, or the new page is not written out")
        after.setdefault(a, []).append(ins["page"])
    new_pages = list(after.get(0, []))
    for i, pg in enumerate(pages, 1):
        if i not in gone:
            new_pages.append(pg)
        new_pages += after.get(i, [])
    out = {**data, **{k: v for k, v in book.items() if k not in ("pages", *KEPT)}}
    out["pages"] = new_pages
    return out


async def revise(book_yaml: str, instruction: str, brief: dict | None = None) -> str:
    """Make one change to the book. Claude sees the book with numbered pages and sends back only what changes;
    everything else is kept as it was, word for word, along with the settings that are not its to change
    (type, paper, language, structure, images). The brief is shown so new words keep its style. Raises when
    nothing changed, with Claude's reason when it gives one."""
    before = yaml.safe_load(book_yaml) or {}
    book_type = before.get("type", BOOK_TYPE)
    fixed = {k: before[k] for k in KEPT if k in before}
    style = (f"\n\nThe brief this book was written from. Every word you write keeps its voice, writing style, "
             f"reading level and learning rules:\n{_brief_text(brief)}") if brief and _brief_text(brief) else ""
    prompt = (f"The book, with each page numbered:\n```yaml\n{numbered(before)}```{style}\n\n"
              f"Make this change: {instruction}\n\nChange only what this asks, and nothing else in the book: "
              f"do not reword, tidy or improve anything it does not mention.\n\n{EDIT_FORMAT}")
    system = _system(book_type)
    text = _fenced(await ask(prompt, system), "yaml")
    retried_empty = False
    for attempt in range(3):
        try:
            patch = yaml.safe_load(text) or {}
            data = apply_patch(before, patch)
            data.update(fixed)
            has_note = isinstance(patch, dict) and bool(patch.get("note"))
            if data == before and not retried_empty and not has_note:
                retried_empty = True   # once: say plainly that nothing changed, and ask again
                text = _fenced(await ask(
                    f"{prompt}\n\nYour previous answer:\n```yaml\n{text}```\nchanged nothing in the book. Make the "
                    "change now, writing out each page or field that changes. Only if the book truly already does "
                    "what is asked, answer with `note:` and why.", system), "yaml")
                continue
            if data == before:
                note = patch.get("note") if isinstance(patch, dict) else None
                raise AuthorError(f"Claude did not change the book: {note}" if note else
                                  "Claude made no change to the book. Say more precisely what should change "
                                  "(which page, which words) and try again.")
            if errs := structure_errors(data):
                raise ValueError("the pages do not follow the book structure: " + "; ".join(errs))
            if errs := activity_errors(data):
                raise ValueError("game pages without their data: " + "; ".join(errs))
            spec.Book.model_validate(data)
            break
        except (ValidationError, ValueError, yaml.YAMLError, TypeError, AttributeError) as e:
            if attempt == 2:
                raise AuthorError(f"Claude's change did not fit the book: {e}") from e
            text = _fenced(await ask(f"{prompt}\n\nYour previous answer:\n```yaml\n{text}```\ncould not be applied:\n"
                                     f"{e}\nFix it and answer again in the same shape.", system), "yaml")
    else:
        raise AuthorError("Claude's change could not be applied. Try again with a shorter request.")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def changed_pages(old_yaml: str, new_yaml: str) -> dict:
    """What an edit changed: the page numbers whose content differs, pages added or removed, other fields."""
    a, b = yaml.safe_load(old_yaml) or {}, yaml.safe_load(new_yaml) or {}
    pa, pb = a.get("pages") or [], b.get("pages") or []
    pages = [i for i, (x, y) in enumerate(zip(pa, pb), 1) if x != y]
    fields = [k for k in dict.fromkeys([*a, *b]) if k != "pages" and a.get(k) != b.get(k)]
    return {"pages": pages, "added": max(0, len(pb) - len(pa)), "removed": max(0, len(pa) - len(pb)),
            "fields": fields}


def activity_errors(data: dict) -> list[str]:
    """Game pages of a template book that are missing the data the software lays them out from."""
    return [f"page {i}: kind {pg.get('kind')!r} needs `{field}`" for i, pg in enumerate(data.get("pages") or [], 1)
            if (field := spec.DATA_KINDS.get((pg or {}).get("kind") or "")) and not pg.get(field)][:8]


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
            if errs := activity_errors(data):
                raise ValueError("game pages without their data: " + "; ".join(errs))
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
        "Draft its Amazon KDP paperback listing for the Amazon store of the book's language: a description "
        "(150-300 words, simple HTML allowed: <b>, <i>, <br>) and exactly 7 search keyword phrases (no title words, "
        "no brand names), both written in the book's language as readers there search, 2-3 browse categories as "
        "full paths, a reading age range, and a one-sentence note on what to declare in KDP's AI-generated content question (images are AI-generated; "
        "say whether text is AI-generated or AI-assisted based on how it was written with you).",
        _system(yaml.safe_load(book_yaml).get("type", "picture_book")), LISTING_SCHEMA)


TRANSLATION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "text"],
        "properties": {"id": {"type": "string"}, "text": {"type": "string"}}}}},
}


def _no_progress(event: str, **info) -> None:
    pass


async def translate(texts: dict[str, str], language: str, source_language: str, check, progress=None) -> dict[str, str]:
    """Translate a finished book's words. `check(original, translated)` lists problems; one retry fixes them.
    `progress(event, **info)` hears what it is doing (see translate_full)."""
    progress = progress or _no_progress
    items = json.dumps([{"id": k, "text": v} for k, v in texts.items()], ensure_ascii=False, indent=1)
    system = ("You are a children's book translator. You translate finished picture books so they read as if "
              "they were written in the target language: natural, warm, rhythmic and age-appropriate, never stiff. "
              "Keep each page about as long as the original, because the words must fit the same space on the page.")
    prompt = (f"Translate this {source_language} children's book into {language}.\n\n"
              "Rules:\n- Return every id exactly once, with its translated text.\n"
              "- Keep line breaks, and keep each [[marked]] passage marked with [[ ]] around its translation "
              "(the same number of marked passages per item).\n"
              "- Character names: keep them, written the way readers of the target language would write them.\n"
              "- Rhymes and wordplay: recreate the effect in the target language rather than translating literally.\n"
              "- ids starting with finds. are short names of things to find in a picture; keep singular/plural "
              "matching the number of things.\n"
              "- learning.marking is the rule for how marked words are chosen: adapt it to the target language.\n\n"
              f"Items:\n{items}")
    for attempt in range(2):
        progress("translate", attempt=attempt)
        out = await ask(prompt, system, TRANSLATION_SCHEMA,
                        on_text=lambda t, a=attempt: progress("text", attempt=a, text=t))
        got = {i["id"]: i["text"] for i in out["items"] if i["id"] in texts}
        errs = check(texts, got)
        if not errs:
            return got
        progress("redo", attempt=attempt, problems=len(errs))
        prompt += ("\n\nYour previous answer had these problems, fix them and return every item again:\n- "
                   + "\n- ".join(errs[:20]))
    raise AuthorError("Claude's translation was incomplete: " + "; ".join(errs[:6]))


FULL_TRANSLATION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items", "adapted"],
    "properties": {
        "items": TRANSLATION_SCHEMA["properties"]["items"],
        "adapted": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["where", "change"],
            "properties": {"where": {"type": "string"}, "change": {"type": "string"}}}}},
}
PLAYTEST_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["problems"],
    "properties": {"problems": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["where", "problem"],
        "properties": {"where": {"type": "string"}, "problem": {"type": "string"}}}}},
}


TRANSLATION_PLAN_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["questions", "auto"],
    "properties": {
        "questions": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "where", "issue", "question", "options"],
            "properties": {"id": {"type": "string"}, "where": {"type": "string"}, "issue": {"type": "string"},
                           "question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}}}},
        "auto": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["where", "change"],
            "properties": {"where": {"type": "string"}, "change": {"type": "string"}}}}},
}


async def translation_plan(texts: dict[str, str], language: str, source_language: str, context: dict) -> dict:
    """Before a full translation: read the lesson and the teaching pages, find the learning points that only
    work in the source language, and ask the author how each should work in the new one.
    Returns {"questions": [{id, where, issue, question, options}], "auto": [{where, change}]}: questions only
    where there is a real choice; obvious adaptations are listed in `auto` so the author sees them too."""
    items = json.dumps([{"id": k, "text": v} for k, v in texts.items()
                        if k.startswith(("learning.", "pages.", "finds."))], ensure_ascii=False, indent=1)
    out = await ask(
        f"This {source_language} children's book is about to get a full translation into {language}: every page, "
        f"every game and every lesson, for a child who reads only {language}. Before anything is translated, "
        "read its lesson and its teaching pages and find what only works in " + source_language + ": games or "
        "rules that hinge on letters, sounds, spelling, rhyme, syllables, word length, alphabetical order or grammar "
        "(articles, gender, plurals, verb forms, word order); a lesson that does not exist in " + language + " (for "
        "example English a/an); fill-in answers, odd-one-out groups or matching pairs that would stop having exactly "
        "one right answer; marked learning words whose rule no longer fits; things a " + language + "-speaking "
        "child would not know (foods, holidays, money, measures, school years).\n\n"
        "For each learning point that breaks AND has more than one sensible way to adapt it, ask the author one "
        "question: `where` is the page (pages.<n> as in Teaching parts) or `learning`; `issue` is one plain "
        f"sentence on what breaks in {language}; `question` asks what to do; `options` are 2-4 concrete choices, "
        f"your recommendation first, each naming the new learning point in {language} with a short example "
        "(e.g. \"Teach un/une instead (un chat, une pomme)\"). The pictures stay as they are, so never offer a "
        "choice that needs a new picture. Ask at most 6 questions, the most important first; group pages that share "
        "one decision into one question (`where` is then the first of them, or `learning`).\n"
        "Put in `auto` each part that breaks but has one obvious fix, with one plain sentence on what will change. "
        "Leave out everything that translates without trouble. Both lists may be empty. Write in plain English for "
        "a non-specialist author, without linguistics terms.\n\n"
        f"Teaching parts:\n{json.dumps(context, ensure_ascii=False, indent=1)}\n\nWords:\n{items}",
        "You are a children's book translator and teacher. You plan translations of educational books so every "
        "lesson and game still teaches something real in the new language, and you ask the author only what "
        "really needs their choice.", TRANSLATION_PLAN_SCHEMA)
    qs = [{**q, "id": q.get("id") or f"q{i + 1}", "options": [o for o in q.get("options") or [] if o.strip()][:4]}
          for i, q in enumerate(out.get("questions") or []) if (q.get("question") or "").strip()][:6]
    return {"questions": qs, "auto": [a for a in out.get("auto") or [] if (a.get("change") or "").strip()]}


def _decisions(decisions: list[dict] | None) -> str:
    rows = [f"- {d.get('where') or 'book'}: {d['question']} -> "
            + ((d.get('answer') or '').strip() or "no answer: you decide") for d in decisions or [] if d.get("question")]
    return ("\n\nThe author answered these questions before the translation. Follow every answer exactly, and "
            "adapt every page it touches so the whole book agrees:\n" + "\n".join(rows)) if rows else ""


async def translate_full(texts: dict[str, str], language: str, source_language: str, check,
                         context: dict, view, decisions: list[dict] | None = None, progress=None) -> dict:
    """A full translation (the workflow is described in bookforge/translate.py).

    `context` is translate.context(book): the lesson and the pages that teach or test something. Without
    any, this is a plain translation. With some, Claude translates and adapts in one pass, `check` catches
    broken structure, and a play-test (`view(translated)` is what the tester reads) catches games and lessons
    that no longer work; each finding goes back to Claude, at most twice.
    Returns {"texts", "adapted": [{where, change}], "unresolved": [{where, problem}]}.

    `progress(event, **info)` hears each step, for the progress shown while it works: "translate" (a pass
    starts, `attempt`), "text" (the answer so far, `text`), "redo" (a pass had `problems` and is done again),
    "playtest" (the teacher plays the games) and "fix" (the play-test found `problems`)."""
    progress = progress or _no_progress
    if not context:
        return {"texts": await translate(texts, language, source_language, check, progress),
                "adapted": [], "unresolved": []}
    items = json.dumps([{"id": k, "text": v} for k, v in texts.items()], ensure_ascii=False, indent=1)
    system = ("You are a children's book translator and teacher. You translate finished educational picture books "
              "so they read as if they were written in the target language, and so every game and lesson works for "
              "a child who reads only that language. Keep each page about as long as the original, because the "
              "words must fit the same space on the page.")
    prompt = (f"Make a full translation of this {source_language} children's book into {language}: every page, "
              "every game and every lesson, the same book for a child who reads only " + language + ".\n\n"
              "Rules:\n- Return every id exactly once, with its translated text.\n"
              "- Keep line breaks, and keep each [[marked]] passage marked with [[ ]] around its translation "
              "(the same number of marked passages per item).\n"
              "- Character names: keep them, written the way readers of the target language would write them.\n"
              "- Rhymes and wordplay: recreate the effect in the target language rather than translating literally.\n"
              "- ids starting with finds. are short names of things to find in a picture; keep singular/plural "
              "matching the number of things.\n\n"
              "Adapting what teaches or tests (the parts under 'Teaching parts'): a word-for-word translation can "
              "break them. For each one, ask whether it still works in " + language + ". It breaks when it hinges "
              "on letters, sounds, spelling, rhyme, syllables, word length, alphabetical order, grammar (articles, "
              "gender, plurals, verb forms, word order), idioms, or things a " + language + "-speaking child would "
              "not know (foods, holidays, money, measures, school years). Watch especially for: a fill-in whose "
              "answer is no longer the one right word for the blank; an odd-one-out group whose odd item no longer "
              "stands out, or where another item now does; matching pairs that are no longer one-to-one; [[marked]] "
              "words that no longer follow the lesson's marking rule; lesson and reference pages that state "
              "something untrue of " + language + ".\n"
              "- If it still works, translate it.\n"
              "- If it would break, adapt it: rewrite it so it teaches the same skill at the same level in "
              f"{language}, with the same number of items. The pictures are kept as they are, so an adapted item "
              "must still fit its page's picture (choose words the picture shows, or that do not refer to it).\n"
              "- If the lesson itself does not exist in " + language + " (for example English a/an), switch to the "
              f"nearest lesson that does (for example un/une in French) and change learning.topic, learning.explain, "
              "learning.marking and every teaching page so they agree.\n"
              "- Change the story itself only where a marked passage requires it.\n"
              "- In `adapted`, list every part you adapted rather than just translated: `where` is the page "
              "(pages.<n>, as in Teaching parts) or `learning`, and `change` is one short plain sentence in "
              "English for the book's author saying what you changed and why. Leave it empty if nothing needed it.\n\n"
              f"Teaching parts:\n{json.dumps(context, ensure_ascii=False, indent=1)}{_decisions(decisions)}\n\n"
              f"Items:\n{items}")
    best = None
    for attempt in range(3):
        progress("translate", attempt=attempt)
        out = await ask(prompt, system, FULL_TRANSLATION_SCHEMA,
                        on_text=lambda t, a=attempt: progress("text", attempt=a, text=t))
        got = {i["id"]: i["text"] for i in out["items"] if i["id"] in texts}
        errs = check(texts, got)
        if errs:
            progress("redo", attempt=attempt, problems=len(errs))
            prompt += ("\n\nYour previous answer had these problems, fix them and return every item again:\n- "
                       + "\n- ".join(errs[:20]))
            continue
        progress("playtest", attempt=attempt)
        problems = await playtest(view(got), language, source_language)
        best = {"texts": got, "adapted": out.get("adapted") or [], "unresolved": problems}
        if not problems or attempt == 2:
            break
        progress("fix", attempt=attempt, problems=len(problems))
        prompt += ("\n\nA teacher play-tested your translation and found these problems. Fix them (adapt the part "
                   "if needed) and return every item and every adaptation again:\n- "
                   + "\n- ".join(f"{p['where']}: {p['problem']}" for p in problems[:20]))
    if best is None:
        raise AuthorError("Claude's translation was incomplete: " + "; ".join(errs[:6]))
    return best


async def playtest(book_yaml: str, language: str, source_language: str) -> list[dict]:
    """Play every game and read every lesson of a translated book as a child who reads only `language`.
    Returns the real problems [{where, problem}], an empty list when everything works."""
    system = (f"You are a {language}-speaking primary school teacher. You play-test children's activity books "
              "before they are printed, and you only report what would really stop or mislead a child.")
    prompt = (f"This book was just translated from {source_language} into {language}. Below are its lesson and "
              "its activity pages (YAML, answers included; `picture` describes the page's illustration, which "
              "cannot change). Do every game and read every lesson as a child who reads only " + language + ".\n\n"
              "Report a problem only when:\n- a game has no correct answer, more than one, or the given answer is "
              "wrong in " + language + ";\n- a game or rule only works in another language (letters, sounds, "
              "rhyme, spelling, grammar);\n- a [[marked]] word does not follow the lesson's marking rule;\n"
              "- a lesson states something untrue of " + language + ";\n- the child is asked to find or name "
              "something the picture does not show;\n- words are left in another language.\n"
              "Ignore style and taste. `where` is the page's `where` value, or `learning`. `problem` is one short "
              "plain sentence in English. Return an empty list when everything works.\n\n"
              f"```yaml\n{book_yaml}```")
    out = await ask(prompt, system, PLAYTEST_SCHEMA)
    return [p for p in out.get("problems") or [] if (p.get("problem") or "").strip()]


TEMPLATE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["name", "description", "sections"],
    "properties": {
        "name": {"type": "string"}, "description": {"type": "string"},
        "sections": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["kind", "pages"],
            "properties": {"kind": {"type": "string", "enum": list(templates.KINDS)},
                           "pages": {"type": "integer"}, "title": {"type": "string"}, "note": {"type": "string"}}}}},
}


async def template_draft(request: str, current: dict | None = None) -> dict:
    """A book structure (name, description, ordered sections) from the writer's own words.
    With `current`, the request changes that structure; without it, Claude starts from scratch."""
    kinds = "\n".join(f"- {k}: {label}. {guide}" for k, (label, guide) in templates.KINDS.items())
    base = ""
    if current and current.get("sections"):
        secs = [s for s in current["sections"] if s.get("enabled", True)]
        base = ("Current structure (change only what the request asks; keep the rest as it is):\n"
                f"name: {current.get('name') or ''}\n" + json.dumps(secs, ensure_ascii=False) + "\n\n")
    prompt = (f"{base}The writer's request: {request}\n\n"
              f"Section kinds you can use:\n{kinds}\n\n"
              "Return the book structure in reading order: each section's kind, its number of interior pages (1-60), "
              "and a title only when the page should not just use the kind's label. Use the custom kind with a note "
              "for anything no kind covers. Keep the name short (2-5 words) and the description to one sentence. "
              "Write the name, description and titles in the language the request is written in.")
    out = await ask(prompt, "You design the structure of children's activity and picture books.", TEMPLATE_SCHEMA)
    out["sections"] = [{k: v for k, v in s.items() if v not in ("", None)} | {"pages": max(0, min(60, int(s.get("pages") or 1)))}
                       for s in out.get("sections", []) if s.get("kind") in templates.KINDS]
    if not out["sections"]:
        raise AuthorError("Claude didn't return any sections. Try saying it another way.")
    return out


async def ping() -> str:
    return (await ask("Reply with the single word: ok", "You are a connectivity check.")).strip()
