"""Canonical visual style/template catalog.

Public fields are safe for the frontend. Prompt guidance stays backend-only.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

_CATALOG_PATH = Path(__file__).with_name("visual_catalog.json")

Compatibility = Literal["preferred", "allowed", "discouraged"]

PUBLIC_STYLE_FIELDS = (
    "id",
    "label_fa",
    "description_fa",
    "preview_path",
    "default_text_safe_area",
    "person_affinity",
    "preferred_templates",
    "discouraged_templates",
)
PUBLIC_TEMPLATE_FIELDS = (
    "id",
    "label_fa",
    "description_fa",
    "preview_path",
    "default_text_safe_area",
    "needs_person",
    "allows_duplicate_products",
    "human_requirement",
    "preferred_styles",
    "discouraged_styles",
)

DISCOURAGED_WARNING_FA = (
    "این ترکیب سبک و قالب معمولاً ضعیف است. می‌تونی ادامه بدی، "
    "ولی نتیجه ممکنه شبیه تبلیغ عمومی بشه."
)


@lru_cache
def _raw() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def styles() -> list[dict[str, Any]]:
    return list(_raw()["styles"])


def templates() -> list[dict[str, Any]]:
    return list(_raw()["templates"])


def style_ids() -> tuple[str, ...]:
    return tuple(item["id"] for item in styles())


def template_ids() -> tuple[str, ...]:
    return tuple(item["id"] for item in templates())


def style_by_id(style_id: str) -> dict[str, Any]:
    match = next((item for item in styles() if item["id"] == style_id), None)
    if match is None:
        raise KeyError(style_id)
    return match


def template_by_id(template_id: str) -> dict[str, Any]:
    match = next((item for item in templates() if item["id"] == template_id), None)
    if match is None:
        raise KeyError(template_id)
    return match


def public_catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        "styles": [_public_style(item) for item in styles()],
        "templates": [_public_template(item) for item in templates()],
    }


def compatibility(style_id: str, template_id: str) -> Compatibility:
    style = style_by_id(style_id)
    template = template_by_id(template_id)
    preferred = template_id in _as_ids(style.get("preferred_templates")) or style_id in _as_ids(
        template.get("preferred_styles")
    )
    discouraged = template_id in _as_ids(
        style.get("discouraged_templates")
    ) or style_id in _as_ids(template.get("discouraged_styles"))
    if (
        template.get("human_requirement") == "required"
        and style.get("person_affinity") == "low"
        and not preferred
    ):
        discouraged = True
    if preferred and discouraged:
        return "allowed"
    if preferred:
        return "preferred"
    if discouraged:
        return "discouraged"
    return "allowed"


def preview_prompt_of(item: dict[str, Any]) -> str:
    return str(item.get("preview_prompt") or item.get("prompt_atoms") or "").strip()


def catalog_digest() -> str:
    """Compact semantics for the Director. Prompt guidance stays out."""
    lines = ["Styles:"]
    for item in styles():
        lines.append(
            f"- {item['id']}: best={_join(item.get('best_for'))}; "
            f"weak={_join(item.get('weak_for'))}; "
            f"person={item.get('person_affinity', 'medium')}; "
            f"identity_risk={item.get('product_identity_risk', 'medium')}; "
            f"preferred_templates={_join(item.get('preferred_templates'))}; "
            f"discouraged_templates={_join(item.get('discouraged_templates'))}"
        )
    lines.append("Templates:")
    for item in templates():
        lines.append(
            f"- {item['id']}: goal={item.get('composition_goal', '')}; "
            f"human={item.get('human_requirement', 'none')}; "
            f"preferred_styles={_join(item.get('preferred_styles'))}; "
            f"discouraged_styles={_join(item.get('discouraged_styles'))}"
        )
    return "\n".join(lines)


def selected_semantics(style_id: str, template_id: str) -> dict[str, Any]:
    style = style_by_id(style_id)
    template = template_by_id(template_id)
    return {
        "style": _architect_style(style),
        "template": _architect_template(template),
        "compatibility": compatibility(style_id, template_id),
    }


def _architect_style(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "label_fa",
        "visual_grammar",
        "composition_tendencies",
        "lighting_tendencies",
        "material_rendering",
        "color_behavior",
        "best_for",
        "weak_for",
        "person_affinity",
        "product_identity_risk",
        "prompt_guidance",
    )
    return {key: item[key] for key in keys if key in item}


def _architect_template(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "label_fa",
        "composition_goal",
        "camera_behavior",
        "product_scale",
        "product_placement",
        "human_requirement",
        "context_requirement",
        "foreground_behavior",
        "background_behavior",
        "text_safe_area_guidance",
        "best_for",
        "weak_for",
        "prompt_guidance",
    )
    return {key: item[key] for key in keys if key in item}


def _public_style(item: dict[str, Any]) -> dict[str, Any]:
    return _pick(item, PUBLIC_STYLE_FIELDS)


def _public_template(item: dict[str, Any]) -> dict[str, Any]:
    picked = _pick(item, PUBLIC_TEMPLATE_FIELDS)
    picked["needs_person"] = item.get("human_requirement") == "required" or bool(
        item.get("needs_person")
    )
    return picked


def _pick(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: item[key] for key in fields if key in item}


def _as_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "—"
    if value:
        return str(value)
    return "—"
