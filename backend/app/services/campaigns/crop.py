"""
Subject crop for messy uploads (Instagram screenshots, letterboxing, chrome).

The original file is never mutated. Crop is a rectangle in 0–1 image space.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, ImageStat

logger = logging.getLogger(__name__)

FULL_CROP = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
MIN_SIDE = 0.12


@dataclass(frozen=True, slots=True)
class CropRect:
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "width": round(self.width, 4),
            "height": round(self.height, 4),
        }


def parse_crop(raw: dict | None) -> CropRect:
    if not raw:
        return CropRect(**FULL_CROP)
    try:
        rect = CropRect(
            x=float(raw["x"]),
            y=float(raw["y"]),
            width=float(raw["width"]),
            height=float(raw["height"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid crop") from error
    if not _valid(rect):
        raise ValueError("invalid crop")
    return rect


def _valid(rect: CropRect) -> bool:
    if rect.width < MIN_SIDE or rect.height < MIN_SIDE:
        return False
    if rect.x < -0.001 or rect.y < -0.001:
        return False
    return rect.x + rect.width <= 1.001 and rect.y + rect.height <= 1.001


def suggest_crop(image_bytes: bytes) -> CropRect:
    """
    Trim uniform letterbox / UI chrome from the edges. A solid product in the
    middle is kept because we only eat low-variance strips attached to the
    border, and we never trim more than 35% per side.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return CropRect(**FULL_CROP)

    width, height = image.size
    if width < 8 or height < 8:
        return CropRect(**FULL_CROP)

    max_top = int(height * 0.35)
    max_side = int(width * 0.35)
    top = _trim_axis(image, "row", 0, 1, max_top)
    bottom = _trim_axis(image, "row", height - 1, -1, max_top)
    left = _trim_axis(image, "col", 0, 1, max_side)
    right = _trim_axis(image, "col", width - 1, -1, max_side)

    y0 = top
    y1 = height - bottom
    x0 = left
    x1 = width - right
    if y1 - y0 < height * 0.2 or x1 - x0 < width * 0.2:
        return CropRect(**FULL_CROP)

    pad_x = (x1 - x0) * 0.03
    pad_y = (y1 - y0) * 0.03
    x0 = max(0.0, x0 - pad_x)
    y0 = max(0.0, y0 - pad_y)
    x1 = min(float(width), x1 + pad_x)
    y1 = min(float(height), y1 + pad_y)

    rect = CropRect(
        x=x0 / width,
        y=y0 / height,
        width=(x1 - x0) / width,
        height=(y1 - y0) / height,
    )
    return rect if _valid(rect) else CropRect(**FULL_CROP)


def apply_crop(image_bytes: bytes, rect: CropRect) -> bytes:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    left = max(0, int(rect.x * width))
    top = max(0, int(rect.y * height))
    right = min(width, int((rect.x + rect.width) * width))
    bottom = min(height, int((rect.y + rect.height) * height))
    if right - left < 2 or bottom - top < 2:
        cropped = image
    else:
        cropped = image.crop((left, top, right, bottom))
    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def _trim_axis(
    image: Image.Image, kind: str, start: int, step: int, limit: int
) -> int:
    """How many uniform border rows/cols to drop from one edge."""
    width, height = image.size
    trimmed = 0
    index = start
    while trimmed < limit:
        if kind == "row":
            if index < 0 or index >= height:
                break
            band = image.crop((0, index, width, index + 1))
        else:
            if index < 0 or index >= width:
                break
            band = image.crop((index, 0, index + 1, height))
        stat = ImageStat.Stat(band.convert("L"))
        std = stat.stddev[0] if stat.stddev else 0
        mean = stat.mean[0] if stat.mean else 0
        # Uniform chrome / letterbox: dark bar, light bar, or low-variance strip.
        if std > 18 and not (mean < 18 or mean > 237):
            break
        if std > 28:
            break
        trimmed += 1
        index += step
    return trimmed
