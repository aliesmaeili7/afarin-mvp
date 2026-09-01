"""
The stored render descriptor for an educational post.

Educational mode does not compose advertising text. The generated image IS the
result, so the spec only records that fact and the image path. AdCanvas,
headline_fa, CTA, price, badges and text_layers stay on the advertising path.
"""

from __future__ import annotations

from typing import Any

RENDER_MODE_EDUCATIONAL = "educational"
RENDER_MODE_ADVERTISING = "advertising"

#: Fields that belong to the advertising compositor. Educational specs must
#: never grow these, or the frontend would start overlaying ad chrome again.
AD_COMPOSITION_KEYS = (
    "template_id",
    "background_id",
    "headline_fa",
    "subheadline_fa",
    "cta_fa",
    "price_text",
    "brand_name",
    "product_image_path",
    "product_source",
    "slide_label_fa",
    "text_layers",
    "scene_image_path",
)


def build_render_spec(*, image_path: str | None) -> dict[str, Any]:
    """
    Explicit mode switch. `render_mode: educational` means: show the image,
    do not hydrate template text, do not draw CTA/badge/price layers.
    """
    return {
        "render_mode": RENDER_MODE_EDUCATIONAL,
        "image_path": image_path,
    }


def is_educational_render_spec(spec: dict[str, Any] | None) -> bool:
    payload = spec or {}
    if payload.get("render_mode") != RENDER_MODE_EDUCATIONAL:
        return False
    return not any(key in payload for key in AD_COMPOSITION_KEYS)
