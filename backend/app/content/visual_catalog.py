"""Unified visual template catalog.

Public fields are safe for the frontend. Creative guidance stays backend-only
and is never concatenated into a Seedream prompt.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("visual_catalog.json")

PUBLIC_TEMPLATE_FIELDS = (
    "id",
    "label_fa",
    "description_fa",
    "preview_path",
    "person_requirement",
)


@lru_cache
def _raw() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def templates() -> list[dict[str, Any]]:
    return list(_raw()["templates"])


def template_ids() -> tuple[str, ...]:
    return tuple(item["id"] for item in templates())


def template_by_id(template_id: str) -> dict[str, Any]:
    match = next((item for item in templates() if item["id"] == template_id), None)
    if match is None:
        raise KeyError(template_id)
    return match


def public_catalog() -> dict[str, list[dict[str, Any]]]:
    return {"templates": [_public_template(item) for item in templates()]}


def preview_prompt_of(item: dict[str, Any]) -> str:
    return str(item.get("preview_prompt") or "").strip()


def catalog_digest() -> str:
    """Compact semantics for the Creative Agent. Prompt text stays out."""
    lines = ["Templates:"]
    for item in templates():
        lines.append(
            f"- {item['id']}: {item.get('label_fa', '')}; "
            f"best={_join(item.get('best_for'))}; "
            f"weak={_join(item.get('weak_for'))}; "
            f"person={item.get('person_requirement', 'none')}; "
            f"identity_risk={item.get('identity_risk', 'medium')}"
        )
    return "\n".join(lines)


def template_semantics(template_id: str | None) -> dict[str, Any] | None:
    if not template_id:
        return None
    item = template_by_id(template_id)
    keys = (
        "id",
        "label_fa",
        "description_fa",
        "creative_guidance",
        "best_for",
        "weak_for",
        "person_requirement",
        "identity_risk",
        "text_safe_area_guidance",
    )
    return {key: item[key] for key in keys if key in item}


def _public_template(item: dict[str, Any]) -> dict[str, Any]:
    picked = {key: item[key] for key in PUBLIC_TEMPLATE_FIELDS if key in item}
    picked["needs_person"] = item.get("person_requirement") == "required"
    return picked


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "—"
    if value:
        return str(value)
    return "—"
