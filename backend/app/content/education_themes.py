"""
Built-in educational themes.

A theme is semantic, not a pasted image prompt: it says what the look IS, and
the Educational Agent decides how to express that for a given topic. So
`creative_guidance` is an input to the agent and is never concatenated onto
`final_prompt` afterwards.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_THEMES_PATH = Path(__file__).with_name("education_themes.json")

#: What the browser is allowed to see. `creative_guidance` stays backend-only,
#: matching the rule that prompts are never exposed to normal users.
PUBLIC_THEME_FIELDS = (
    "id",
    "name",
    "source",
    "palette",
    "illustration_style",
    "mood",
    "lighting",
    "shape_language",
    "decorative_motifs",
    "background_treatment",
)


@lru_cache
def _raw() -> dict[str, Any]:
    return json.loads(_THEMES_PATH.read_text(encoding="utf-8"))


def builtin_themes() -> list[dict[str, Any]]:
    return [dict(item) for item in _raw()["themes"]]


def builtin_theme_ids() -> tuple[str, ...]:
    return tuple(item["id"] for item in _raw()["themes"])


def get_builtin(theme_id: str) -> dict[str, Any]:
    match = next(
        (item for item in _raw()["themes"] if item["id"] == theme_id), None
    )
    if match is None:
        raise KeyError(theme_id)
    return dict(match)


def find_builtin(theme_id: str | None) -> dict[str, Any] | None:
    if not theme_id:
        return None
    try:
        return get_builtin(theme_id)
    except KeyError:
        return None


def public_builtin_themes() -> list[dict[str, Any]]:
    return [_public(item) for item in builtin_themes()]


def _public(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item[key] for key in PUBLIC_THEME_FIELDS if key in item}
