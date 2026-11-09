"""The character directory: once a character's sheet is made, its look is locked and reused.

    books/<slug>/characters/<char-id>/sheet.png        the reference attached to every page
    books/<slug>/characters/<char-id>/character.yaml   name, the exact description, where it came from

Every locked character is also published to the shared library (~/.bookforge/characters/), so the
next book of a series that declares a character with the same name starts from the same look.
Mock runs lock into build/characters-mock/ and never touch the library.
"""
from __future__ import annotations

import datetime
import hashlib
import shutil
from pathlib import Path

import yaml

from . import settings
from .project import Project
from .spec import Character

def library_dir() -> Path:
    """The shared library, next to the studio settings (follows BOOKFORGE_HOME)."""
    return settings.home() / "characters"


def char_id(name: str) -> str:
    return f"char-{name.lower().replace(' ', '-')}"


def _entry(root: Path, name: str) -> Path:
    return root / char_id(name).removeprefix("char-")


def _info(d: Path) -> dict | None:
    f = d / "character.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() and (d / "sheet.png").exists() else None


def locked(project: Project, c: Character) -> Path | None:
    """The locked reference sheet for this character, if there is one."""
    sheet = _entry(project.characters, c.name) / "sheet.png"
    return sheet if sheet.exists() else None


def info(project: Project, c: Character) -> dict | None:
    return _info(_entry(project.characters, c.name))


def _write(d: Path, png: Path, data: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    if png.resolve() != (d / "sheet.png").resolve():
        shutil.copyfile(png, d / "sheet.png")
    (d / "character.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))


def lock(project: Project, c: Character, png: Path) -> None:
    """Remember this sheet as the character's look, in the book and in the shared library."""
    data = {
        "name": c.name,
        "description": c.description.strip(),
        "source_book": project.book.title,
        "locked_at": datetime.date.today().isoformat(),
        "art_model": project.book.images.model,
        "style_hash": hashlib.sha256(project.book.style.strip().encode()).hexdigest()[:12],
    }
    _write(_entry(project.characters, c.name), png, data)
    if not project.mock:
        _write(_entry(library_dir(), c.name), png, data)


def adopt(project: Project, log=print) -> None:
    """Fill the book's directory before any art is made: sheets from an earlier run of this book
    are locked as they are; otherwise a library character with the same name is copied in."""
    for c in project.book.characters:
        if locked(project, c):
            continue
        earlier = project.art_path(char_id(c.name))
        if earlier.exists():
            lock(project, c, earlier)
            log(f"  locked {c.name} from this book's existing sheet")
        elif not project.mock and (lib := _info(_entry(library_dir(), c.name))):
            _write(_entry(project.characters, c.name), _entry(library_dir(), c.name) / "sheet.png", lib)
            log(f"  {c.name}: reusing the library character from {lib.get('source_book', 'another book')!r}")


def description(project: Project, c: Character) -> str:
    """The locked wording when there is one, so every prompt repeats it word for word."""
    entry = info(project, c)
    return entry["description"] if entry else c.description


def drifted(project: Project) -> list[str]:
    """Characters whose book.yaml description no longer matches the locked one."""
    out = []
    for c in project.book.characters:
        entry = info(project, c)
        if entry and " ".join(entry["description"].split()) != " ".join(c.description.split()):
            out.append(c.name)
    return out


def reset(project: Project, name: str) -> bool:
    """Unlock one character so the next art run draws (and locks) a new sheet. The library copy stays."""
    d = _entry(project.characters, name)
    if not d.exists():
        return False
    shutil.rmtree(d)
    project.art_path(char_id(name)).unlink(missing_ok=True)
    return True


def listing(project: Project) -> list[dict]:
    return [{"name": c.name, "locked": bool(locked(project, c)), **(info(project, c) or {})}
            for c in project.book.characters]


def library() -> list[dict]:
    """Every character drawn for any book, with `id` (its folder) for the web library."""
    lib = library_dir()
    if not lib.is_dir():
        return []
    return [{**i, "id": d.name} for d in sorted(lib.iterdir()) if (i := _info(d))]


def _library_dir(cid: str) -> Path | None:
    lib = library_dir().resolve()
    d = (lib / cid).resolve()
    return d if d.parent == lib and _info(d) else None


def library_sheet(cid: str) -> Path | None:
    d = _library_dir(cid)
    return d / "sheet.png" if d else None


def remove_from_library(cid: str) -> bool:
    """Forget a library character. Books that already locked it keep their own copy."""
    d = _library_dir(cid)
    if d:
        shutil.rmtree(d)
    return bool(d)


def replace_library_sheet(cid: str, data: bytes) -> None:
    """Use the writer's own image as this character's look in future books. Raises ValueError if unusable."""
    import io

    from PIL import Image
    d = _library_dir(cid)
    if not d:
        raise ValueError(f"no library character {cid!r}")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.convert("RGB").save(d / "sheet.png")
    except Exception as e:
        raise ValueError(f"not an image: {e}") from e


PACK_MARKER = "bookforge-characters.json"  # identifies a character file made by export_pack
_MAX_SHEET_BYTES = 30 * 1024 * 1024


def export_pack(ids: list[str] | None = None) -> bytes:
    """Library characters (all, or just `ids`) as one .zip to send to another studio: per character
    its character.yaml and sheet.png, plus a marker listing who is inside."""
    import io
    import json
    import zipfile

    lib = library()
    if ids is not None:
        lib = [c for c in lib if c["id"] in set(ids)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(PACK_MARKER, json.dumps({"characters": [c["name"] for c in lib]}, ensure_ascii=False, indent=1))
        for c in lib:
            d = library_dir() / c["id"]
            z.write(d / "character.yaml", f"{c['id']}/character.yaml")
            z.write(d / "sheet.png", f"{c['id']}/sheet.png")
    return buf.getvalue()


def import_pack(data: bytes) -> dict:
    """Add the characters in an exported .zip to this library. A character with the same name is
    replaced by the imported look. Returns {"added": [...], "replaced": [...]}. Raises ValueError."""
    import io
    import zipfile

    from PIL import Image
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError("That isn't a character file (expected the .zip made by Export).") from e
    names = set(z.namelist())
    folders = sorted({n.split("/")[0] for n in names if n.endswith("/character.yaml") and n.count("/") == 1})
    if not folders:
        raise ValueError("No characters found in that file.")
    added, replaced = [], []
    for f in folders:
        if f"{f}/sheet.png" not in names:
            continue
        try:
            meta = yaml.safe_load(z.read(f"{f}/character.yaml"))
            name = str(meta["name"]).strip()
            if not name or z.getinfo(f"{f}/sheet.png").file_size > _MAX_SHEET_BYTES:
                continue
            with Image.open(io.BytesIO(z.read(f"{f}/sheet.png"))) as im:
                im.load()
                png = io.BytesIO()
                im.convert("RGB").save(png, "PNG")
        except Exception:
            continue
        keep = {k: meta[k] for k in ("name", "description", "source_book", "locked_at", "art_model", "style_hash")
                if k in meta}
        keep["name"] = name
        keep["description"] = str(keep.get("description", "")).strip()
        d = _entry(library_dir(), name)
        if d.resolve().parent != library_dir().resolve():
            continue  # a name that would escape the library folder
        (replaced if _info(d) else added).append(name)
        d.mkdir(parents=True, exist_ok=True)
        (d / "sheet.png").write_bytes(png.getvalue())
        (d / "character.yaml").write_text(yaml.safe_dump(keep, sort_keys=False, allow_unicode=True, width=100))
    if not added and not replaced:
        raise ValueError("None of the characters in that file could be read.")
    return {"added": added, "replaced": replaced}
