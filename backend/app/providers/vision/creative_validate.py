"""Hard invariants for Unified Creative Agent JSON. Never rewrites final_prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.content.visual_catalog import template_ids

# Re-exported so existing advertising imports keep working after the move to
# app.providers.llm.base, where it sits beside LlmUsage itself.
from app.providers.llm.base import merge_llm_usage
from app.providers.vision.base import CreativeAgentResult, CreativeImage

__all__ = [
    "FINAL_PROMPT_MAX_CHARS",
    "CreativeValidation",
    "correction_user_block",
    "merge_llm_usage",
    "validate_creative_result",
]

FINAL_PROMPT_MAX_CHARS = 800
_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_HEADING_LINE_RE = re.compile(r"(?m)^(PRESERVE|OUTPUT|VISUAL EXECUTION|DO NOT ADD)\s*$")
_SECTION_HEADINGS = ("VISUAL EXECUTION", "DO NOT ADD")


@dataclass(frozen=True, slots=True)
class CreativeValidation:
    ok: bool
    errors: tuple[str, ...]

    def as_dict(self, *, retry_used: bool = False) -> dict:
        return {
            "ok": self.ok,
            "retry_used": retry_used,
            "errors": list(self.errors),
        }


def validate_creative_result(
    result: CreativeAgentResult,
    *,
    requested_image_count: int,
) -> CreativeValidation:
    errors: list[str] = []
    images = result.images
    if len(images) != requested_image_count:
        errors.append(
            f"expected {requested_image_count} images, got {len(images)}"
        )
        return CreativeValidation(ok=False, errors=tuple(errors))

    known = set(template_ids())
    prompts = [item.final_prompt.strip() for item in images]
    if requested_image_count > 1 and len(set(prompts)) != requested_image_count:
        errors.append("image final_prompts must differ")

    if requested_image_count > 1:
        signatures = [
            (
                item.visual_plan.scene.strip().lower(),
                item.visual_plan.composition.strip().lower(),
                item.visual_plan.camera.strip().lower(),
                item.visual_plan.text_safe_area.position.strip().lower(),
            )
            for item in images
        ]
        if len(set(signatures)) == 1:
            errors.append(
                "concepts are identical on scene, composition, camera, "
                "and text_safe_area.position"
            )

    for index, item in enumerate(images, start=1):
        errors.extend(_image_errors(item, index, known_ids=known))
    return CreativeValidation(ok=not errors, errors=tuple(errors))


def correction_user_block(errors: tuple[str, ...] | list[str]) -> str:
    lines = ["Previous JSON failed validation. Fix only these issues:"]
    lines.extend(f"- {error}" for error in errors)
    lines.append("Return a new JSON object with the requested image count.")
    lines.append(
        "final_prompt is the only Seedream text: one short paragraph, max 800 "
        "characters, no headings, bullets, or JSON."
    )
    return "\n".join(lines)


def _image_errors(
    item: CreativeImage, index: int, *, known_ids: set[str]
) -> list[str]:
    prefix = f"image {index}"
    errors: list[str] = []
    prompt = item.final_prompt.strip()
    if not prompt:
        errors.append(f"{prefix}: final_prompt is empty")
    elif len(prompt) > FINAL_PROMPT_MAX_CHARS:
        errors.append(
            f"{prefix}: final_prompt exceeds {FINAL_PROMPT_MAX_CHARS} characters"
        )
    elif _looks_like_json(prompt) or _has_section_dump(prompt):
        errors.append(f"{prefix}: final_prompt looks like JSON or a section dump")
    elif "4:5" not in prompt and "4 x 5" not in prompt.lower():
        errors.append(f"{prefix}: final_prompt must represent the 4:5 format")

    template_id = item.visual_plan.template_id
    if template_id and template_id not in known_ids:
        errors.append(f"{prefix}: unknown template_id {template_id!r}")

    safe = item.visual_plan.text_safe_area
    if not safe.position.strip():
        errors.append(f"{prefix}: text_safe_area.position is empty")
    if not safe.description.strip():
        errors.append(f"{prefix}: text_safe_area.description is empty")

    if not any(row.strip() for row in item.identity.must_preserve):
        errors.append(f"{prefix}: identity.must_preserve is required")

    copy = item.copy
    for field, value in (
        ("on_image_headline", copy.on_image_headline),
        ("feed_caption", copy.feed_caption),
        ("story_text", copy.story_text),
        ("cta", copy.cta),
    ):
        text = (value or "").strip()
        if not text:
            errors.append(f"{prefix}: copy.{field} is empty")
        elif not _PERSIAN_RE.search(text):
            errors.append(f"{prefix}: copy.{field} must be Persian")
    if not copy.hashtags:
        errors.append(f"{prefix}: copy.hashtags is empty")
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
