"""Deterministic creative reference preparation.

Never send the original upload to the image model. Seedream receives the
approved crop, re-encoded as JPEG.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

from app.core import messages
from app.core.errors import invalid

MIN_REFERENCE_PX = 256


@dataclass(frozen=True, slots=True)
class PrepResult:
    strategy: str
    jpeg: bytes | None
    blocked: bool
    reasons: tuple[str, ...] = ()
    used_cutout: bool = False


async def prepare_clean_jpeg(
    *,
    original: bytes | None = None,
    crop_jpeg: bytes | None,
    analysis: dict | None = None,
) -> PrepResult:
    del original, analysis
    if crop_jpeg is None:
        return PrepResult(
            "needs_user_action",
            None,
            True,
            ("missing approved crop",),
        )
    jpeg, quality = _as_clean_jpeg(crop_jpeg)
    if quality is not None:
        return PrepResult("needs_user_action", None, True, (quality,))
    return PrepResult("direct_crop", jpeg, False)


def assert_not_blocked(result: PrepResult) -> bytes:
    if result.blocked or result.jpeg is None:
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)
    return result.jpeg


def _as_clean_jpeg(content: bytes) -> tuple[bytes | None, str | None]:
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception:
        return None, "unreadable reference"
    if min(image.size) < MIN_REFERENCE_PX:
        return None, "reference too small"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92, optimize=True)
    return buffer.getvalue(), None
