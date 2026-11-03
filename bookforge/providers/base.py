from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ImageProvider(Protocol):
    name: str
    model: str

    def request_size(self, aspect: float) -> tuple[int, int]:
        """Best pixel size this model can produce for width/height ratio `aspect`."""

    def generate(self, prompt: str, size: tuple[int, int], refs: list[Path], quality: str | None = None) -> bytes:
        """Return PNG/JPEG bytes. `refs` are reference images for character consistency."""


def get_provider(settings) -> ImageProvider:
    if settings.provider == "mock":
        from .mock import MockProvider
        return MockProvider(settings.max_pixels)
    from .openai_images import OpenAIProvider
    return OpenAIProvider(settings.model, settings.quality, settings.max_pixels)
