"""Deterministic creative reference preparation.

Never send the original upload to the image model. If cutout/rembg fails or
the mask looks contaminated, block paid generation instead of degrading to
the dirty screenshot.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

from app.core import messages
from app.core.errors import invalid
from app.services.campaigns.crop import CropRect, apply_crop, clamp_crop, parse_crop
from app.services.campaigns.cutout import get_cutout

logger = logging.getLogger(__name__)

MIN_REFERENCE_PX = 256
NEUTRAL_RGB = (243, 241, 236)
MIN_SUBJECT_FRACTION = 0.04
MAX_SUBJECT_FRACTION = 0.97
MIN_BBOX_FRACTION = 0.08

STRATEGIES = (
    "direct_crop",
    "tighter_crop",
    "subject_cutout_neutral",
    "preserve_context_crop",
    "needs_user_action",
)


@dataclass(frozen=True, slots=True)
class PrepResult:
    strategy: str
    jpeg: bytes | None
    blocked: bool
    reasons: tuple[str, ...] = ()
    used_cutout: bool = False


def analysis_strategy(analysis: dict | None) -> str:
    raw = (analysis or {}).get("reference_strategy") or "direct_crop"
    return raw if raw in STRATEGIES else "direct_crop"


def recommended_crop_rect(analysis: dict | None) -> CropRect | None:
    raw = (analysis or {}).get("recommended_crop")
    if not isinstance(raw, dict):
        return None
    try:
        return clamp_crop(parse_crop(raw))
    except ValueError:
        return None


def decide_strategy(analysis: dict | None) -> str:
    """Safety overrides on top of Director output."""
    payload = analysis or {}
    strategy = analysis_strategy(payload)
    if (
        payload.get("brief_image_mismatch")
        or payload.get("product_visibility") == "unusable"
    ):
        return "needs_user_action"
    cleanliness = str(payload.get("cleanliness") or "")
    if cleanliness == "overlapping_contamination":
        return "needs_user_action"
    if (
        payload.get("person_present") or payload.get("useful_context_present")
    ) and strategy == "subject_cutout_neutral":
        return "preserve_context_crop"
    if strategy == "needs_user_action":
        return strategy
    return strategy


async def prepare_clean_jpeg(
    *,
    original: bytes | None,
    crop_jpeg: bytes | None,
    analysis: dict | None,
) -> PrepResult:
    """
    Build the bytes Seedream may receive.

    Never returns the original upload. Failure to cut out an isolatable
    subject becomes needs_user_action, not a dirty fallback.
    """
    strategy = decide_strategy(analysis)
    if strategy == "needs_user_action":
        reasons = tuple(
            str(item)
            for item in (analysis or {}).get("blocking_reasons")
            or ("needs_user_action",)
        )
        return PrepResult(strategy, None, True, reasons)

    if crop_jpeg is None:
        return PrepResult(
            "needs_user_action",
            None,
            True,
            ("missing approved crop",),
        )

    if strategy == "subject_cutout_neutral":
        cut = await get_cutout().remove_background(crop_jpeg)
        checked = validate_cutout_png(cut)
        if checked is None:
            logger.warning("creative cutout failed or looked contaminated; blocking")
            return PrepResult(
                "needs_user_action",
                None,
                True,
                ("cutout failed",),
            )
        jpeg = _composite_neutral(checked)
        quality = _validate_reference_jpeg(jpeg)
        if quality is not None:
            return PrepResult("needs_user_action", None, True, (quality,))
        return PrepResult(strategy, jpeg, False, used_cutout=True)

    # direct_crop, tighter_crop (already accepted), preserve_context_crop
    quality = _validate_reference_jpeg(crop_jpeg)
    if quality is not None:
        return PrepResult("needs_user_action", None, True, (quality,))
    return PrepResult(strategy, crop_jpeg, False)


def apply_recommended_crop(original: bytes, analysis: dict | None) -> bytes | None:
    rect = recommended_crop_rect(analysis)
    if rect is None:
        return None
    return apply_crop(original, rect)


def assert_not_blocked(result: PrepResult) -> bytes:
    if result.blocked or result.jpeg is None:
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)
    return result.jpeg


def validate_cutout_png(png: bytes | None) -> bytes | None:
    if not png:
        return None
    try:
        image = Image.open(io.BytesIO(png))
    except Exception:
        return None
    if min(image.size) < MIN_REFERENCE_PX:
        return None
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    hist = alpha.histogram()
    opaque = sum(hist[32:])
    total = rgba.size[0] * rgba.size[1]
    if total <= 0:
        return None
    fraction = opaque / total
    if fraction < MIN_SUBJECT_FRACTION or fraction > MAX_SUBJECT_FRACTION:
        return None
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    box_w = (right - left) / rgba.size[0]
    box_h = (bottom - top) / rgba.size[1]
    if box_w < MIN_BBOX_FRACTION or box_h < MIN_BBOX_FRACTION:
        return None
    return png


async def extract_validated_cutout(image_jpeg: bytes) -> bytes | None:
    """Best-effort rembg cutout. Failure returns None; never blocks transform."""
    try:
        cut = await get_cutout().remove_background(image_jpeg)
    except Exception:
        logger.warning("cutout extraction failed", exc_info=True)
        return None
    return validate_cutout_png(cut)


def _composite_neutral(png: bytes) -> bytes:
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    canvas = Image.new("RGB", image.size, NEUTRAL_RGB)
    canvas.paste(image, mask=image.split()[3])
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def _validate_reference_jpeg(jpeg: bytes) -> str | None:
    try:
        image = Image.open(io.BytesIO(jpeg))
        width, height = image.size
    except Exception:
        return "unreadable reference"
    if min(width, height) < MIN_REFERENCE_PX:
        return "reference too small"
    return None
