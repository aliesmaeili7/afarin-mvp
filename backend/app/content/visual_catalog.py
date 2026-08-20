"""Canonical visual style/template catalog.

Public fields are safe for the frontend. `prompt_atoms` stay backend-only.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("visual_catalog.json")

PUBLIC_STYLE_FIELDS = (
    "id",
    "label_fa",
    "description_fa",
    "preview_path",
    "default_text_safe_area",
)
PUBLIC_TEMPLATE_FIELDS = (
    *PUBLIC_STYLE_FIELDS,
    "needs_person",
    "allows_duplicate_products",
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
        "styles": [_pick(item, PUBLIC_STYLE_FIELDS) for item in styles()],
        "templates": [_pick(item, PUBLIC_TEMPLATE_FIELDS) for item in templates()],
    }


def _pick(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: item[key] for key in fields if key in item}
