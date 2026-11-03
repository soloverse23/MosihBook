from __future__ import annotations

from pathlib import Path

from . import spec


class Project:
    def __init__(self, book_path: str | Path, mock: bool = False):
        self.book_path = Path(book_path).resolve()
        self.root = self.book_path.parent
        self.book = spec.load(self.book_path)
        if mock:
            self.book.images.provider = "mock"
        self.build = self.root / "build"
        self.cache = self.build / "cache"
        self.art = self.build / ("art-mock" if self.mock else "art")
        self.prepared = self.build / "prepared"
        self.proofs = self.build / "proofs"
        for d in (self.cache, self.art, self.prepared, self.proofs):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def mock(self) -> bool:
        return self.book.images.provider == "mock"

    @property
    def characters(self) -> Path:
        """The book's character directory (see characters.py); mock runs keep theirs in build/."""
        return self.build / "characters-mock" if self.mock else self.root / "characters"

    def art_path(self, slot_id: str) -> Path:
        return self.art / f"{slot_id}.png"

    @property
    def interior_pdf(self) -> Path:
        return self.build / "interior.pdf"

    @property
    def cover_pdf(self) -> Path:
        return self.build / "cover.pdf"

    @property
    def manifest(self) -> Path:
        return self.build / "manifest.json"
