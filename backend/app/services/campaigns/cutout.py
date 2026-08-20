"""
Local unpaid background removal.

The seller's pixels never go through an image model. If rembg is missing or
fails, the caller composites the seller-approved crop — never the raw
screenshot — and tells the seller that this happened.
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Protocol

from PIL import Image

logger = logging.getLogger(__name__)


class CutoutBackend(Protocol):
    async def remove_background(self, image_bytes: bytes) -> bytes | None: ...


class RembgCutout:
    async def remove_background(self, image_bytes: bytes) -> bytes | None:
        try:
            from rembg import remove
        except ImportError:
            logger.warning(
                "rembg is not installed; campaigns will use the seller's crop"
            )
            return None

        try:
            result = await asyncio.to_thread(remove, image_bytes)
        except Exception:
            logger.exception("product cutout failed")
            return None

        if not isinstance(result, bytes | bytearray) or not result:
            return None
        return bytes(result)


class NullCutout:
    """Explicit no-op used in tests for the rembg-missing path."""

    async def remove_background(self, image_bytes: bytes) -> bytes | None:
        return None


class PassthroughCutout:
    """Tests inject this so a cutout row exists without pulling onnxruntime."""

    async def remove_background(self, image_bytes: bytes) -> bytes | None:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        except Exception:
            return None
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


_backend: CutoutBackend | None = None


def rembg_available() -> bool:
    try:
        import rembg  # noqa: F401
    except ImportError:
        return False
    return True


def get_cutout() -> CutoutBackend:
    global _backend
    if _backend is None:
        _backend = RembgCutout()
    return _backend


def set_cutout(backend: CutoutBackend | None) -> None:
    """Test seam. Production never calls this."""
    global _backend
    _backend = backend
