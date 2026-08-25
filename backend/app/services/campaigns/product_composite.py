"""Paste a validated product cutout onto a generated empty scene.

Not AdCanvas. Scale, optional small rotation, and a contact shadow only.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFilter

from app.providers.vision.base import ProductPlacement

MIN_COVERAGE = 0.08
MAX_COVERAGE = 0.52
MAX_CLIP_FRACTION = 0.05


def composite_cutout_onto_scene(
    scene_jpeg: bytes,
    cutout_png: bytes,
    placement: ProductPlacement,
) -> bytes:
    scene = Image.open(io.BytesIO(scene_jpeg)).convert("RGB")
    cutout = Image.open(io.BytesIO(cutout_png)).convert("RGBA")
    canvas_w, canvas_h = scene.size
    target_w = max(8, int(round(placement.width * canvas_w)))
    scale = target_w / max(1, cutout.size[0])
    target_h = max(8, int(round(cutout.size[1] * scale)))
    product = cutout.resize((target_w, target_h), Image.Resampling.LANCZOS)
    angle = -placement.rotation_degrees
    if abs(angle) > 0.05:
        product = product.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    cx = int(round(placement.x * canvas_w))
    cy = int(round(placement.y * canvas_h))
    left = cx - product.size[0] // 2
    top = cy - product.size[1] // 2
    layer = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    shadow = _contact_shadow(product, placement)
    shadow_dx, shadow_dy = _shadow_offset(placement.shadow_direction, max(product.size))
    layer.paste(shadow, (left + shadow_dx, top + shadow_dy), shadow)
    layer.paste(product, (left, top), product)
    composed = Image.alpha_composite(scene.convert("RGBA"), layer).convert("RGB")
    buffer = io.BytesIO()
    composed.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def composite_looks_plausible(
    composed_jpeg: bytes,
    cutout_png: bytes,
    placement: ProductPlacement,
) -> bool:
    del cutout_png
    image = Image.open(io.BytesIO(composed_jpeg)).convert("RGB")
    width, height = image.size
    target_w = placement.width * width
    target_h = target_w * 1.25
    left = placement.x * width - target_w / 2
    top = placement.y * height - target_h / 2
    right = left + target_w
    bottom = top + target_h
    clip = 0.0
    if left < 0:
        clip += -left * target_h
    if top < 0:
        clip += -top * target_w
    if right > width:
        clip += (right - width) * target_h
    if bottom > height:
        clip += (bottom - height) * target_w
    box_area = max(1.0, target_w * target_h)
    if clip / box_area > MAX_CLIP_FRACTION:
        return False
    coverage = box_area / max(1, width * height)
    return MIN_COVERAGE <= coverage <= MAX_COVERAGE


def _contact_shadow(product: Image.Image, placement: ProductPlacement) -> Image.Image:
    width, height = product.size
    ellipse_h = max(4, height // 8)
    ellipse = Image.new("L", (width, ellipse_h), 0)
    draw = ImageDraw.Draw(ellipse)
    draw.ellipse((0, 0, width - 1, ellipse_h - 1), fill=140)
    softness = (placement.shadow_softness or "soft").lower()
    radius = 6 if "hard" in softness else 12
    ellipse = ellipse.filter(ImageFilter.GaussianBlur(radius=radius))
    blob = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    blob.paste((0, 0, 0, 160), (0, height - ellipse_h), ellipse)
    return blob


def _shadow_offset(direction: str, size: int) -> tuple[int, int]:
    mag = max(2, size // 18)
    text = (direction or "down").lower()
    dx = 0
    dy = mag
    if "left" in text:
        dx = -mag
    elif "right" in text:
        dx = mag
    if "up" in text:
        dy = -mag // 3
    return dx, dy
