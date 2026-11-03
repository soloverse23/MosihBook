from __future__ import annotations

import base64
import time
from contextlib import ExitStack
from pathlib import Path

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
        self.client = OpenAI()
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
        for attempt in range(5):
            try:
                if refs:
                    with ExitStack() as stack:
                        files = [stack.enter_context(open(r, "rb")) for r in refs[:MAX_REFS]]
                        resp = self.client.images.edit(
                            model=self.model, image=files, prompt=prompt,
                            size=size_str, quality=quality,
                        )
                else:
                    resp = self.client.images.generate(
                        model=self.model, prompt=prompt, size=size_str, quality=quality,
                    )
                return base64.b64decode(resp.data[0].b64_json)
            except Exception as e:
                if "moderation_blocked" in str(e):
                    raise ModerationBlocked(str(e)) from e
                status = getattr(e, "status_code", None)  # retry rate limits and transient 5xx
                if status not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise
                time.sleep(2 ** attempt * 5)
        raise RuntimeError("unreachable")
