"""Validate and apply free-positioned Persian type on an AssetRenderSpec."""

from __future__ import annotations

import re
from typing import Any

from app.core import messages
from app.core.errors import invalid

MAX_TEXT_LAYERS = 10
MAX_LAYER_TEXT = 200
MIN_VISIBLE = 0.3
ALLOWED_FONTS = frozenset({"vazirmatn", "estedad", "gandom", "amiri", "lalezar"})
UNIQUE_ROLES = frozenset(
    {"headline", "subheadline", "cta", "price", "brand", "slide_label"}
)
ALL_ROLES = UNIQUE_ROLES | {"custom"}
ALIGNS = frozenset({"right", "center", "left"})
BACKGROUNDS = frozenset({"none", "pill", "rect"})
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ROLE_FIELDS = {
    "headline": "headline_fa",
    "subheadline": "subheadline_fa",
    "cta": "cta_fa",
    "price": "price_text",
    "brand": "brand_name",
    "slide_label": "slide_label_fa",
}


def apply_text_layers(spec: dict[str, Any], layers: list[Any] | None) -> dict[str, Any]:
    """Replace or clear `text_layers`. None restores the legacy flex layout."""
    next_spec = dict(spec)
    if layers is None:
        next_spec.pop("text_layers", None)
        return next_spec
    parsed = parse_text_layers(layers)
    next_spec["text_layers"] = parsed
    return sync_content_fields(next_spec, parsed)


def apply_role_text(spec: dict[str, Any], role: str, text: str) -> dict[str, Any]:
    """Keep a role layer's copy in sync when headline/CTA is rewritten."""
    next_spec = dict(spec)
    layers = next_spec.get("text_layers")
    if not isinstance(layers, list):
        return next_spec
    updated: list[dict[str, Any]] = []
    for layer in layers:
        if not isinstance(layer, dict):
            updated.append(layer)
            continue
        if layer.get("role") == role:
            updated.append({**layer, "text": text[:MAX_LAYER_TEXT]})
        else:
            updated.append(layer)
    next_spec["text_layers"] = updated
    return next_spec


def parse_text_layers(raw: list[Any]) -> list[dict[str, Any]]:
    if len(raw) > MAX_TEXT_LAYERS:
        raise invalid(messages.TEXT_LAYERS_LIMIT)
    if len(raw) == 0:
        raise invalid(messages.TEXT_LAYERS_INVALID)
    parsed: list[dict[str, Any]] = []
    ids: set[str] = set()
    seen_roles: set[str] = set()
    for item in raw:
        layer = _parse_layer(item)
        if layer["id"] in ids:
            raise invalid(messages.TEXT_LAYERS_INVALID)
        role = layer["role"]
        if role != "custom":
            if role in seen_roles:
                raise invalid(messages.TEXT_LAYERS_INVALID)
            seen_roles.add(role)
        ids.add(layer["id"])
        parsed.append(layer)
    return parsed


def sync_content_fields(
    spec: dict[str, Any], layers: list[dict[str, Any]]
) -> dict[str, Any]:
    next_spec = dict(spec)
    for layer in layers:
        role = layer.get("role")
        field = ROLE_FIELDS.get(role) if isinstance(role, str) else None
        if not field:
            continue
        text = str(layer.get("text") or "").strip()
        if field == "headline_fa":
            next_spec[field] = text or str(layer.get("text") or "")
        else:
            next_spec[field] = text or None
    return next_spec


def _parse_layer(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise invalid(messages.TEXT_LAYERS_INVALID)
    layer_id = str(raw.get("id") or "").strip()
    role = raw.get("role")
    if not layer_id or len(layer_id) > 64 or role not in ALL_ROLES:
        raise invalid(messages.TEXT_LAYERS_INVALID)
    text = str(raw.get("text") or "")[:MAX_LAYER_TEXT]
    font_family = raw.get("font_family")
    if font_family not in ALLOWED_FONTS:
        font_family = "vazirmatn"
    color = raw.get("color")
    if not isinstance(color, str) or not HEX.match(color):
        color = "#ffffff"
    background_color = raw.get("background_color")
    if not (isinstance(background_color, str) and HEX.match(background_color)):
        background_color = None
    width = _clamp(_num(raw.get("width"), 0.8), 0.12, 1.0)
    visible = width * MIN_VISIBLE
    return {
        "id": layer_id,
        "role": role,
        "text": text,
        "x": _clamp(_num(raw.get("x"), 0.1), visible - width, 1 - visible),
        "y": _clamp(_num(raw.get("y"), 0.4), -0.15, 0.92),
        "width": width,
        "font_family": font_family,
        "font_size": _clamp(_num(raw.get("font_size"), 0.06), 0.024, 0.22),
        "font_weight": 700 if _num(raw.get("font_weight"), 400) == 700 else 400,
        "color": color,
        "text_align": raw.get("text_align") if raw.get("text_align") in ALIGNS else "center",
        "opacity": _clamp(_num(raw.get("opacity"), 1), 0.15, 1.0),
        "background": (
            raw.get("background") if raw.get("background") in BACKGROUNDS else "none"
        ),
        "background_color": background_color,
        "background_opacity": _clamp(_num(raw.get("background_opacity"), 0.55), 0, 1),
        "shadow": bool(raw.get("shadow")),
    }


def _num(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return number


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
