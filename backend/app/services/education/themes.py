"""
The educational theme system.

A theme is style memory only: palette, material/look, mood, lighting, character
feel and motifs. It is never a layout, never fonts, never CTA/badge/price
chrome, and never the lesson of the post it came from.

`sanitize_theme` is what enforces that. Reusing a theme should give a familiar
look, not the same picture and not extra overlay text.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.education_themes import find_builtin, public_builtin_themes
from app.db.models import EducationalTheme
from app.providers.education.base import EducationalTheme as AgentTheme

#: Everything a saved theme may contain. Anything outside this set is post
#: content or advertising layout and must not survive into a reusable theme.
THEME_KEYS = (
    "name",
    "palette",
    "illustration_style",
    "mood",
    "lighting",
    "shape_language",
    "decorative_motifs",
    "background_treatment",
    "creative_guidance",
)

#: Post-specific or advertising keys we actively refuse, named so the intent
#: is testable.
POST_ONLY_KEYS = (
    "educational_concept",
    "content",
    "visual_plan",
    "final_prompt",
    "headline",
    "subtitle",
    "caption",
    "hashtags",
    "overlay_items",
    "language",
    "typography",
    "text_treatment",
    "font_role",
    "headline_fa",
    "cta_fa",
    "price_text",
    "text_layers",
    "template_id",
)

DEFAULT_MOOD = "warm and clear"
DEFAULT_LIGHTING = "soft even lighting"


def theme_from_agent(theme: AgentTheme) -> dict[str, Any]:
    """Turns the agent's designed theme into the stored theme shape."""
    return {
        "name": theme.name_suggestion,
        "palette": {
            "primary": list(theme.primary_colors),
            "secondary": list(theme.secondary_colors),
        },
        "illustration_style": theme.illustration_style,
        "mood": theme.mood,
        "lighting": theme.lighting,
        "shape_language": theme.shape_language,
        "decorative_motifs": list(theme.decorative_motifs),
    }


def sanitize_theme(raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Keeps only reusable visual semantics, and normalizes them so a saved theme
    can be fed straight back to the agent later.
    """
    source = raw or {}
    palette = source.get("palette") or {}
    cleaned: dict[str, Any] = {
        "palette": {
            "primary": _colors(palette.get("primary")),
            "secondary": _colors(palette.get("secondary")),
        },
        "illustration_style": _text(source.get("illustration_style")),
        "mood": _text(source.get("mood")) or DEFAULT_MOOD,
        "lighting": _text(source.get("lighting")) or DEFAULT_LIGHTING,
        "shape_language": _text(source.get("shape_language")),
        "decorative_motifs": _strings(source.get("decorative_motifs")),
    }
    background_treatment = _text(source.get("background_treatment"))
    if background_treatment:
        cleaned["background_treatment"] = background_treatment
    for key in ("background", "text"):
        value = _text(palette.get(key))
        if value:
            cleaned["palette"][key] = value
    guidance = _text(source.get("creative_guidance"))
    if guidance:
        cleaned["creative_guidance"] = guidance
    name = _text(source.get("name"))
    if name:
        cleaned["name"] = name
    return cleaned


def agent_theme_input(theme: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    What the agent receives for a selected theme. `creative_guidance` is
    included here deliberately: it is guidance for the model, and the agent
    reasons about it rather than us pasting it onto the image prompt.
    """
    if not theme:
        return None
    return sanitize_theme(theme)


async def list_saved_themes(
    session: AsyncSession, user_id: uuid.UUID
) -> list[EducationalTheme]:
    rows = await session.scalars(
        select(EducationalTheme)
        .where(EducationalTheme.user_id == user_id)
        .order_by(EducationalTheme.created_at.desc())
    )
    return list(rows)


async def resolve_theme(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    theme_id: uuid.UUID | None,
    builtin_id: str | None,
) -> dict[str, Any] | None:
    """
    Loads whichever theme the user picked. A saved theme is checked against the
    caller so one account cannot read another's design.
    """
    if theme_id is not None:
        row = await session.scalar(
            select(EducationalTheme).where(
                EducationalTheme.id == theme_id,
                EducationalTheme.user_id == user_id,
            )
        )
        return sanitize_theme(row.theme_json) if row else None
    builtin = find_builtin(builtin_id)
    return sanitize_theme(builtin) if builtin else None


def builtin_catalog() -> list[dict[str, Any]]:
    return public_builtin_themes()


def theme_name_of(theme: dict[str, Any] | None, fallback: str) -> str:
    return _text((theme or {}).get("name")) or fallback


def _colors(value: Any) -> list[str]:
    return [
        item.strip()
        for item in _strings(value)
        if item.strip().startswith("#") and len(item.strip()) == 7
    ]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _text(value: Any) -> str:
    return str(value or "").strip()
