from __future__ import annotations

import base64
import time
from contextlib import ExitStack
from pathlib import Path

from ..settings import openai_key as _openai_key

MAX_REFS = 6
# gpt-image-2 / 2.5 take any WxH that is a multiple of 16, within these bounds
FLEX_MAX_EDGE = 3840
FLEX_MAX_PIXELS = 3840 * 2160
FLEX_MIN_PIXELS = 655_360
FIXED_SIZES = [(1024, 1024), (1536, 1024), (1024, 1536)]


class ModerationBlocked(Exception):
    """OpenAI refused the prompt or the output; the prompt needs rewording."""


def flex_size(aspect: float, max_pixels: int = FLEX_MAX_PIXELS) -> tuple[int, int]:
    """Largest flexible size for this width/height ratio within `max_pixels`."""
    aspect = min(max(aspect, 1 / 3), 3)
    max_pixels = min(max(max_pixels, FLEX_MIN_PIXELS), FLEX_MAX_PIXELS)
    h = (max_pixels / aspect) ** 0.5
    w = h * aspect
    scale = min(1.0, FLEX_MAX_EDGE / max(w, h))
    w, h = int(w * scale) // 16 * 16, int(h * scale) // 16 * 16
    if w * h < FLEX_MIN_PIXELS:  # rounding down can dip under the floor
        w, h = w + 16, h + 16
    return w, h


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str, quality: str, max_pixels: int):
        from openai import OpenAI  # imported lazily so mock runs need no key
        self.client = OpenAI(api_key=_openai_key())
        self.model = model
        self.quality = quality
        self.max_pixels = max_pixels

    @property
    def flexible(self) -> bool:
        return self.model.startswith("gpt-image-2")  # gpt-image-2 and gpt-image-2.5-*

    def request_size(self, aspect: float) -> tuple[int, int]:
        if not self.flexible:
            return min(FIXED_SIZES, key=lambda s: abs(s[0] / s[1] - aspect))
        return flex_size(aspect, self.max_pixels)

    def generate(self, prompt: str, size: tuple[int, int], refs: list[Path], quality: str | None = None) -> bytes:
        size_str = f"{size[0]}x{size[1]}"
        quality = quality or self.quality

        def call():
            if refs:
                with ExitStack() as stack:
                    files = [stack.enter_context(open(r, "rb")) for r in refs[:MAX_REFS]]
                    return self.client.images.edit(model=self.model, image=files, prompt=prompt,
                                                   size=size_str, quality=quality)
            return self.client.images.generate(model=self.model, prompt=prompt, size=size_str, quality=quality)
        return self._retry(call)

    def extend(self, image: bytes, mask: bytes, prompt: str, size: tuple[int, int],
               quality: str | None = None) -> bytes:
        """Paint the transparent part of `mask` (PNG, alpha 0 = paint here) over `image`: an outpaint."""
        size_str = f"{size[0]}x{size[1]}"
        quality = quality or self.quality
        try:
            return self._retry(lambda: self.client.images.edit(
                model=self.model, image=("page.png", image, "image/png"), mask=("mask.png", mask, "image/png"),
                prompt=prompt, size=size_str, quality=quality))
        except ModerationBlocked:
            raise
        except Exception as e:
            if "mask" not in str(e).lower():
                raise
            # a model that takes no mask still sees the picture with its plain border to paint; the caller
            # pastes the original back over the middle either way
            return self._retry(lambda: self.client.images.edit(
                model=self.model, image=("page.png", image, "image/png"), prompt=prompt,
                size=size_str, quality=quality))

    def _retry(self, call) -> bytes:
        for attempt in range(5):
            try:
                return base64.b64decode(call().data[0].b64_json)
            except Exception as e:
                if "moderation_blocked" in str(e):
                    raise ModerationBlocked(str(e)) from e
                status = getattr(e, "status_code", None)  # retry rate limits and transient 5xx
                if status not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise
                time.sleep(2 ** attempt * 5)
        raise RuntimeError("unreachable")
