"""bookforge: story + illustration prompts in, KDP-ready interior.pdf and cover.pdf out."""
from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import characters as chars
from . import storymd
from .art import generate
from .art.lint import lint
from .layout.cover import build_cover
from .layout.render import build_interior
from .plan import plan as plan_slots
from .preflight import check, proofs
from .project import Project

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()
Book = typer.Argument(..., help="path to book.yaml")
Mock = typer.Option(False, "--mock", help="placeholder art: free, offline")


@app.command()
def init(out: Path = typer.Argument(Path("book.yaml")),
         from_md: Path = typer.Option(None, "--from", help="convert a story.md into book.yaml")):
    """Create a book.yaml (from a story.md, or a starter template)."""
    if out.exists():
        raise typer.BadParameter(f"{out} already exists")
    out.write_text(storymd.convert(from_md.read_text()) if from_md else storymd.TEMPLATE)
    console.print(f"wrote {out}")


@app.command()
def plan(book: Path = Book):
    """Show every illustration the book needs and the estimated image cost."""
    p = Project(book)
    slots = plan_slots(p.book)
    table = Table("slot", "kind", "aspect", "characters")
    for s in slots:
        table.add_row(s.id, s.kind, f"{s.aspect:.2f}", ", ".join(s.characters))
    console.print(table)
    s = p.book.images
    est = sum(s.cost(x.id) for x in slots)
    console.print(f"{len(slots)} images with {s.model} ({s.quality}) - estimated ${est:.2f} "
                  f"(at ${s.est_cost_per_image_usd}/image, {len(s.high_quality)} at high; each image is generated "
                  "once, cached images are free)")
    _lint(p)


@app.command()
def pilot(book: Path = Book, mock: bool = Mock,
          pages: int = typer.Option(3, help="how many page illustrations to try")):
    """Try the look first: character sheets + cover + the first few illustrations, then review.html."""
    p = Project(book, mock)
    _lint(p, strict=True)
    generate.run(p, pilot=pages)
    console.print(f"open {p.build / 'review.html'} - happy? run `bookforge all`. Not yet? adjust style/"
                  "characters in book.yaml (or `regen --note`) and pilot again")


@app.command()
def art(book: Path = Book, mock: bool = Mock,
        only: list[str] = typer.Option(None, "--only", help="slot id(s) to generate"),
        force: bool = typer.Option(False, help="ignore prompt-check errors")):
    """Generate character sheets, cover, then all illustrations, each reviewed (cached)."""
    p = Project(book, mock)
    _lint(p, strict=not force)
    generate.run(p, set(only) if only else None)


@app.command()
def regen(book: Path = Book, slots: list[str] = typer.Argument(..., help="slot ids, e.g. p007 cover-front"),
          note: str = typer.Option(None, help="art-director note added to these prompts, e.g. 'Pip smaller, facing left'"),
          mock: bool = Mock):
    """Redo specific illustrations (fresh attempts), optionally with a correction note."""
    generate.run(Project(book, mock), set(slots), bump=set(slots),
                 notes={s: note for s in slots} if note else None)


characters_app = typer.Typer(help="The character directory: each character's locked look.")
app.add_typer(characters_app, name="characters")


@characters_app.command("list")
def characters_list(book: Path = Book, mock: bool = Mock):
    """Show which characters are locked, and the shared library."""
    p = Project(book, mock)
    table = Table("character", "locked", "since", "from book")
    for c in chars.listing(p):
        table.add_row(c["name"], "yes" if c["locked"] else "no (drawn on the next art run)",
                      c.get("locked_at", ""), c.get("source_book", ""))
    console.print(table)
    console.print(f"directory: {p.characters}")
    lib = chars.library()
    console.print(f"library ({chars.library_dir()}): " + (", ".join(c["name"] for c in lib) or "empty"))


@characters_app.command("reset")
def characters_reset(book: Path = Book, name: str = typer.Argument(..., help="character name as in book.yaml"),
                     mock: bool = Mock):
    """Unlock a character so the next art run draws a new sheet (pages that show it need a regen too)."""
    p = Project(book, mock)
    if not chars.reset(p, name):
        raise typer.BadParameter(f"{name!r} is not locked in {p.characters}")
    console.print(f"{name} unlocked - run `bookforge art` to draw and lock a new sheet")


def _lint(p: Project, strict: bool = False) -> None:
    issues = lint(p.book)
    for i in issues:
        color = "red" if i.level == "error" else "yellow"
        console.print(f"[{color}]{i.level.upper():5}[/] {i.where}: {i.message}")
    if not issues:
        console.print("[green]prompt check: no issues[/]")
    if strict and any(i.level == "error" for i in issues):
        console.print("fix the errors above or pass --force")
        raise typer.Exit(1)


@app.command()
def build(book: Path = Book, mock: bool = Mock):
    """Lay out interior.pdf and cover.pdf from the generated art, then preflight."""
    p = Project(book, mock)
    m = build_interior(p)
    console.print(f"interior: {m['pages']} pages -> {p.interior_pdf}")
    c = build_cover(p)
    console.print(f"cover: {c['size_in'][0]:.3f} x {c['size_in'][1]:.3f} in, spine {c['spine_in']:.3f} in -> {p.cover_pdf}")
    _preflight(p)


@app.command()
def preflight(book: Path = Book, mock: bool = Mock):
    """Validate the PDFs against KDP rules and render proofs + preview.html."""
    _preflight(Project(book, mock))


@app.command(name="all")
def all_(book: Path = Book, mock: bool = Mock):
    """art + build + preflight in one go."""
    p = Project(book, mock)
    _lint(p, strict=True)
    if generate.run(p):
        console.print("[yellow]some images need attention - see review.html; building anyway[/]")
    build_interior(p)
    build_cover(p)
    _preflight(p)


def _preflight(p: Project) -> None:
    report = check(p)
    proofs(p)
    for e in report["errors"]:
        console.print(f"[red]ERROR[/] {e}")
    for w in report["warnings"]:
        console.print(f"[yellow]WARN[/]  {w}")
    status = "[green]PASS[/]" if report["ok"] else "[red]FAIL[/]"
    console.print(f"preflight {status} - proofs in {p.proofs}, open {p.build / 'preview.html'}")
    if not report["ok"]:
        raise typer.Exit(1)


@app.command("claude-login")
def claude_login():
    """Sign in to Claude (your subscription) for MosiBooks, in this terminal."""
    import subprocess

    from .web.app import _claude_bin
    exe = _claude_bin()
    if not exe:
        console.print("[red]Claude Code not found. Run: pip install -e '.[web]'[/red]")
        raise typer.Exit(1)
    raise typer.Exit(subprocess.call([exe, "auth", "login", "--claudeai"]))


@app.command()
def serve(port: int = typer.Option(8765, help="port"),
          host: str = typer.Option("127.0.0.1", help="use 0.0.0.0 on a server (needs MOSIBOOKS_PASSWORD)"),
          open_browser: bool = typer.Option(True, "--open/--no-open", help="open the browser")):
    """Start MosiBooks, the local web UI (needs: pip install -e ".[web]")."""
    import threading
    import webbrowser

    import uvicorn

    from . import settings
    settings.load().apply_env()
    if host not in ("127.0.0.1", "localhost") and not os.environ.get("MOSIBOOKS_PASSWORD"):
        console.print("[red]Refusing to listen on a public address without a login. "
                      "Set MOSIBOOKS_PASSWORD (and optionally MOSIBOOKS_USER).[/red]")
        raise typer.Exit(1)
    url = f"http://127.0.0.1:{port}"
    console.print(f"MosiBooks on {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    uvicorn.run("bookforge.web.app:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
