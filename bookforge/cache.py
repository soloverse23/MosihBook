"""Content-addressed image cache: identical requests are never paid for twice."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def request_key(model: str, prompt: str, size: tuple[int, int], refs: list[Path], variation: int) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "size": list(size),
        "refs": [file_hash(r) for r in refs], "variation": variation,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class JsonStore:
    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))
