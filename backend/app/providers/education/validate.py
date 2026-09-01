"""
Hard invariants for Educational Agent JSON.

This checks; it never rewrites. A valid `final_prompt` is passed to the image
provider byte for byte. An invalid response earns exactly one correction round.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.enums import EDUCATION_LANGUAGES
from app.providers.education.base import EducationalPostResult
from app.providers.education.prompts import FINAL_PROMPT_MAX_CHARS

_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_SQUARE_TOKENS = ("1:1", "square", "مربع", "مربعی")
_SECTION_HEADINGS = ("VISUAL PLAN", "FINAL PROMPT", "THEME", "CONTENT", "OUTPUT")
_HEADING_LINE_RE = re.compile(r"(?m)^(VISUAL PLAN|THEME|CONTENT|OUTPUT)\s*$")
#: Phrases that mean the agent is still targeting an overlay compositor.
_OVERLAY_PIPELINE_RE = re.compile(
    r"leave (?:a |the )?(?:clean |empty )?(?:space|band|area).{0,40}"
    r"(?:title|headline|overlay|text)|"
    r"(?:don't|do not) (?:draw|paint|render|typeset).{0,40}"
    r"(?:title|headline|wording|text)|"
    r"later (?:overlay|overlaid)|"
    r"(?:added|placed) (?:on top|over).{0,20}(?:afterwards|later)|"
    r"عنوان.{0,20}(?:خالی|نکش|بعدا)|"
    r"متن.{0,20}(?:بعداً|بعدا |روی تصویر)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class EducationalValidation:
    ok: bool
    errors: tuple[str, ...]

    def as_dict(self, *, retry_used: bool = False) -> dict:
        return {
            "ok": self.ok,
            "retry_used": retry_used,
            "errors": list(self.errors),
        }


def validate_educational_result(
    result: EducationalPostResult,
    *,
    theme_was_selected: bool = False,
) -> EducationalValidation:
    errors: list[str] = []
    errors.extend(_language_errors(result))
    errors.extend(_prompt_errors(result))
    # A user-selected theme wins outright, so the agent's theme block is not
    # used and not worth failing the whole call over.
    if not theme_was_selected:
        errors.extend(_theme_errors(result))
    return EducationalValidation(ok=not errors, errors=tuple(errors))


def correction_user_block(errors: tuple[str, ...] | list[str]) -> str:
    lines = ["Your previous JSON failed validation. Fix only these issues:"]
    lines.extend(f"- {error}" for error in errors)
    lines.append(
        "Return a corrected JSON object with the same structure. final_prompt "
        f"is the only text the image model sees: one paragraph, at most "
        f"{FINAL_PROMPT_MAX_CHARS} characters, no headings, bullets or JSON. "
        "Describe a finished poster. Do not reserve overlay space."
    )
    return "\n".join(lines)


def _language_errors(result: EducationalPostResult) -> list[str]:
    if result.language not in EDUCATION_LANGUAGES:
        return [
            f"language must be one of {', '.join(EDUCATION_LANGUAGES)}, "
            f"got {result.language!r}"
        ]
    errors: list[str] = []
    checked = (("final_prompt", result.final_prompt),)
    for field, value in checked:
        text = (value or "").strip()
        if not text:
            continue
        if result.language == "fa" and not _PERSIAN_RE.search(text):
            errors.append(f"{field} must be written in Persian")
        if result.language == "en" and _PERSIAN_RE.search(text):
            errors.append(f"{field} must be written in English only")
    return errors


def _prompt_errors(result: EducationalPostResult) -> list[str]:
    prompt = result.final_prompt.strip()
    if not prompt:
        return ["final_prompt is empty"]
    if len(prompt) > FINAL_PROMPT_MAX_CHARS:
        return [
            f"final_prompt exceeds {FINAL_PROMPT_MAX_CHARS} characters "
            f"(got {len(prompt)})"
        ]
    if _looks_like_json(prompt) or _has_section_dump(prompt):
        return ["final_prompt looks like JSON or a section dump"]
    lowered = prompt.lower()
    if not any(token in lowered for token in _SQUARE_TOKENS):
        return ["final_prompt must describe the square 1:1 format"]
    if _OVERLAY_PIPELINE_RE.search(prompt):
        return [
            "final_prompt must describe a finished poster, not an overlay "
            "compositor (do not reserve empty title space)"
        ]
    return []


def _theme_errors(result: EducationalPostResult) -> list[str]:
    errors: list[str] = []
    theme = result.theme
    if not theme.name_suggestion.strip():
        errors.append("theme.name_suggestion is empty")
    if not theme.primary_colors:
        errors.append("theme.primary_colors needs at least one color")
    for label, colors in (
        ("primary_colors", theme.primary_colors),
        ("secondary_colors", theme.secondary_colors),
    ):
        for color in colors:
            if not _HEX_RE.match((color or "").strip()):
                errors.append(
                    f"theme.{label} entry {color!r} must be #rrggbb hex"
                )
    for field, value in (
        ("illustration_style", theme.illustration_style),
        ("mood", theme.mood),
        ("lighting", theme.lighting),
        ("shape_language", theme.shape_language),
    ):
        if not (value or "").strip():
            errors.append(f"theme.{field} is empty")
    return errors


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return (
        stripped.startswith("{")
        or stripped.startswith("[")
        or stripped.startswith("```")
    )


def _has_section_dump(text: str) -> bool:
    if any(heading in text for heading in _SECTION_HEADINGS):
        return True
    return bool(_HEADING_LINE_RE.search(text))
