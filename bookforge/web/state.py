"""Where Studio books live: books/<slug>/book.yaml plus studio.json (wizard state)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from .. import settings, spec

STEPS = ["brief", "questions", "outline", "manuscript", "preview", "art", "publish"]


def books_dir() -> Path:
    d = Path(settings.load().books_dir).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "book"
    slug, n = base, 2
    while (books_dir() / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def book_dir(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise KeyError(slug)
    d = books_dir() / slug
    if not d.is_dir():
        raise KeyError(slug)
    return d


def load_state(slug: str) -> dict:
    p = book_dir(slug) / "studio.json"
    return json.loads(p.read_text()) if p.exists() else {"step": "manuscript"}


def save_state(slug: str, **updates) -> dict:
    state = {**load_state(slug), **updates}
    (book_dir(slug) / "studio.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))
    return state


def create(brief: dict) -> str:
    slug = slugify(brief.get("title") or brief.get("idea") or "book")
    (books_dir() / slug).mkdir(parents=True)
    save_state(slug, step="brief", brief=brief)
    return slug


# ---- reference files the writer attaches to the brief -------------------------------------

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
SOURCE_TYPES = (".pdf", ".txt", ".md", ".docx") + IMAGE_TYPES
MAX_SOURCE_CHARS = 80_000  # all attachments together, as sent to Claude


def _extract(name: str, data: bytes) -> str:
    ext = Path(name).suffix.lower()
    if ext in IMAGE_TYPES:  # images go to Claude as pictures; the text file just marks them in the list
        from PIL import Image
        import io
        Image.open(io.BytesIO(data)).verify()
        return f"[image {name}: attached to this message as a picture]"
    if ext == ".pdf":
        import io
        from pypdf import PdfReader
        return "\n\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
    if ext == ".docx":
        import io
        import zipfile
        from xml.etree import ElementTree
        w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        root = ElementTree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
        return "\n".join("".join(t.text or "" for t in p.iter(f"{w}t")) for p in root.iter(f"{w}p"))
    return data.decode("utf-8", errors="replace")


def add_source(slug: str, name: str, data: bytes) -> dict:
    """Save an attachment and its extracted text. Raises ValueError if it is unusable."""
    name = Path(name).name.strip()
    if not name or Path(name).suffix.lower() not in SOURCE_TYPES:
        raise ValueError(f"attach {', '.join(SOURCE_TYPES)} files")
    try:
        text = _extract(name, data).strip()
    except Exception as e:
        raise ValueError(f"could not read {name}: {e}") from e
    if not text:
        raise ValueError(f"{name} has no readable text (a scanned PDF needs OCR first, or attach its pages as images)")
    d = book_dir(slug) / "sources"
    (d / "text").mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(data)
    (d / "text" / f"{name}.txt").write_text(text)
    return {"name": name, "bytes": len(data), "chars": len(text)}


def remove_source(slug: str, name: str) -> None:
    d = book_dir(slug) / "sources"
    for f in (d / Path(name).name, d / "text" / f"{Path(name).name}.txt"):
        f.unlink(missing_ok=True)


def sources(slug: str) -> list[dict]:
    d = book_dir(slug) / "sources"
    return [{"name": f.name, "bytes": f.stat().st_size, "chars": len((d / "text" / f"{f.name}.txt").read_text())}
            for f in sorted(d.iterdir()) if f.is_file() and (d / "text" / f"{f.name}.txt").exists()] \
        if d.is_dir() else []


def source_images(slug: str) -> list[Path]:
    """The attached image files, sent to Claude alongside the text."""
    d = book_dir(slug) / "sources"
    return [d / s["name"] for s in sources(slug) if Path(s["name"]).suffix.lower() in IMAGE_TYPES]


def sources_text(slug: str) -> str:
    """Every attachment's text, labelled by file name, cut to MAX_SOURCE_CHARS in total."""
    d = book_dir(slug) / "sources" / "text"
    parts = [f"=== {s['name']} ===\n{(d / (s['name'] + '.txt')).read_text()}" for s in sources(slug)]
    text = "\n\n".join(parts)
    if len(text) > MAX_SOURCE_CHARS:
        text = text[:MAX_SOURCE_CHARS] + "\n\n[... the rest of the attachments was cut for length]"
    return text


def read_yaml(slug: str) -> str | None:
    p = book_dir(slug) / "book.yaml"
    return p.read_text() if p.exists() else None


def validate_yaml(text: str) -> str | None:
    """None if the yaml is a valid book, else the error message."""
    try:
        spec.Book.model_validate(yaml.safe_load(text))
        return None
    except (ValidationError, yaml.YAMLError, TypeError) as e:
        return str(e)


def pages_view(text: str | None) -> list[dict]:
    """The manuscript as the reader view shows it: text, art prompt, chapter, panel count."""
    try:
        pages = (yaml.safe_load(text or "") or {}).get("pages") or []
    except (yaml.YAMLError, AttributeError):
        return []
    return [{"text": p.get("text", ""), "prompt": p.get("prompt") or "", "chapter": p.get("chapter") or "",
             "layout": p.get("layout") or "", "panels": len(p.get("panels") or []), "kind": p.get("kind") or ""}
            for p in pages if isinstance(p, dict)]


def write_yaml(slug: str, text: str) -> None:
    (book_dir(slug) / "book.yaml").write_text(text)


def summary(slug: str) -> dict:
    d = book_dir(slug)
    state = load_state(slug)
    text = read_yaml(slug)
    title, book_type = (state.get("brief") or {}).get("title") or slug, (state.get("brief") or {}).get("type")
    if text:
        try:
            data = yaml.safe_load(text)
            title, book_type = data.get("title", title), data.get("type", book_type)
        except yaml.YAMLError:
            pass
    pf = d / "build" / "preflight.json"
    preflight = json.loads(pf.read_text()) if pf.exists() else None
    built = state.get("last_build")
    if preflight and built == "real":
        status = "ready" if preflight["ok"] else "preflight failed"
    elif built == "mock":
        status = "mock preview"
    elif text:
        status = "manuscript"
    else:
        status = "draft"
    proof = d / "build" / "proofs" / "cover.png"
    return {"slug": slug, "title": title, "type": book_type, "step": state.get("step"), "status": status,
            "last_build": built, "cover": proof.exists(), "pages": (preflight or {}).get("pages"),
            "updated": max((p.stat().st_mtime for p in d.glob("*") if p.is_file()), default=0)}


def all_books() -> list[dict]:
    out = []
    for d in books_dir().iterdir():
        if d.is_dir() and ((d / "studio.json").exists() or (d / "book.yaml").exists()):
            try:
                out.append(summary(d.name))
            except KeyError:
                continue
    return sorted(out, key=lambda b: -b["updated"])
