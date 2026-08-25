"""Hard invariants for Prompt Architect JSON. Never rewrites final_prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.providers.llm.base import LlmUsage
from app.providers.vision.base import ArchitectCandidate, PromptArchitectResult
from app.services.campaigns.render_strategy import (
    PRESERVED_PRODUCT_COMPOSITE,
    REFERENCE_TRANSFORM,
    placement_can_integrate,
)

FINAL_PROMPT_MAX_CHARS = 800

_SECTION_HEADINGS = (
    "VISUAL EXECUTION",
    "DO NOT ADD",
)
_HEADING_LINE_RE = re.compile(r"(?m)^(PRESERVE|OUTPUT)\s*$")
_SPACE_RE = re.compile(r"\s+")

_NEGATED_DRAW = (
    "do not draw the product",
    "don't draw the product",
    "do not render the product",
    "don't render the product",
    "do not generate the product",
    "leave the product out",
    "no product drawn",
    "without the product",
)

_PRODUCT_AS_SUBJECT = (
    "this exact product",
    "the referenced product",
    "the attached product",
    "the cleaned reference",
    "draw this product",
    "draw the product",
    "render the product",
    "photograph this product",
    "show this product",
    "the product as the hero",
    "hero of this exact",
    "keep this product in",
    "place this product",
    "the seller product in the scene",
)


@dataclass(frozen=True, slots=True)
class ArchitectValidation:
    ok: bool
    errors: tuple[str, ...]

    def as_dict(
        self, *, retry_used: bool = False, switched_to_transform: bool = False
    ) -> dict:
        payload = {
            "ok": self.ok,
            "retry_used": retry_used,
            "errors": list(self.errors),
        }
        if switched_to_transform:
            payload["switched_to_transform"] = True
        return payload


def validate_architect_result(
    result: PromptArchitectResult,
    *,
    render_strategy: str,
    identity_constraints: list[str] | tuple[str, ...] = (),
    template_id: str = "",
) -> ArchitectValidation:
    errors: list[str] = []
    candidates = result.candidates
    if len(candidates) != 3:
        errors.append(f"expected 3 candidates, got {len(candidates)}")
        return ArchitectValidation(ok=False, errors=tuple(errors))

    slots = [item.slot for item in candidates]
    if sorted(slots) != [1, 2, 3] or len(set(slots)) != 3:
        errors.append("slots must be unique 1, 2, and 3")
    intentions = [item.intention for item in candidates]
    if sorted(intentions) != ["bold", "editorial", "safe"] or len(set(intentions)) != 3:
        errors.append("intentions must be unique safe, editorial, and bold")

    prompts = [item.final_prompt.strip() for item in candidates]
    if len(set(prompts)) != 3:
        errors.append("candidate final_prompts must differ")

    signatures = [
        (
            item.composition.camera.strip().lower(),
            item.scene.environment.strip().lower(),
            item.composition.product_position.strip().lower(),
            item.typography_safe_area.position.strip().lower(),
        )
        for item in candidates
    ]
    if len(set(signatures)) == 1:
        errors.append(
            "candidates are identical on camera, environment, product_position, "
            "and typography_safe_area.position"
        )

    for item in candidates:
        errors.extend(
            _candidate_errors(
                item,
                render_strategy=render_strategy,
                identity_constraints=identity_constraints,
                template_id=template_id,
            )
        )
    return ArchitectValidation(ok=not errors, errors=tuple(errors))


def placement_unusable(validation: ArchitectValidation) -> bool:
    return any(
        "unusable product placement" in error or "not scene-only" in error
        for error in validation.errors
    )


def correction_user_block(
    errors: tuple[str, ...] | list[str],
    *,
    switch_to_transform: bool,
) -> str:
    lines = ["Previous JSON failed validation. Fix only these issues:"]
    lines.extend(f"- {error}" for error in errors)
    if switch_to_transform:
        lines.append(
            "Switch render_strategy to reference_transform. Write a new full-image "
            "final_prompt for each candidate that describes this exact product in "
            "the scene. Do not reuse a scene-only prompt. Do not tell the image "
            "model to omit the product."
        )
    else:
        lines.append("Keep the same render_strategy. Return a new JSON object.")
    lines.append(
        "final_prompt is the only Seedream text: one short paragraph, max 800 "
        "characters, no headings, bullets, or JSON."
    )
    return "\n".join(lines)


def merge_llm_usage(first: LlmUsage | None, second: LlmUsage | None) -> LlmUsage | None:
    if first is None:
        return second
    if second is None:
        return first
    cost = None
    if first.cost_usd is not None or second.cost_usd is not None:
        cost = (first.cost_usd or Decimal("0")) + (second.cost_usd or Decimal("0"))
    return LlmUsage(
        prompt_tokens=_add_int(first.prompt_tokens, second.prompt_tokens),
        completion_tokens=_add_int(first.completion_tokens, second.completion_tokens),
        latency_ms=_add_int(first.latency_ms, second.latency_ms),
        cost_usd=cost,
        model=second.model or first.model,
    )


def _candidate_errors(
    item: ArchitectCandidate,
    *,
    render_strategy: str,
    identity_constraints: list[str] | tuple[str, ...],
    template_id: str,
) -> list[str]:
    prefix = f"slot {item.slot}"
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

    if item.output.aspect_ratio != "4:5":
        errors.append(f"{prefix}: output.aspect_ratio must be 4:5")
    if not item.typography_safe_area.position.strip():
        errors.append(f"{prefix}: typography_safe_area.position is empty")
    if not item.typography_safe_area.description.strip():
        errors.append(f"{prefix}: typography_safe_area.description is empty")
    if identity_constraints and not any(row.strip() for row in item.must_preserve):
        errors.append(
            f"{prefix}: must_preserve is required when identity constraints exist"
        )
    if item.render_strategy != render_strategy:
        errors.append(
            f"{prefix}: render_strategy {item.render_strategy!r} does not match "
            f"{render_strategy!r}"
        )

    if render_strategy == PRESERVED_PRODUCT_COMPOSITE:
        ok, reason = placement_can_integrate(item, template_id=template_id)
        if not item.has_product_placement or not ok:
            errors.append(f"{prefix}: unusable product placement: {reason}")
        if prompt and not _is_scene_only(prompt):
            errors.append(f"{prefix}: preserved final_prompt is not scene-only")
    elif render_strategy == REFERENCE_TRANSFORM:
        if item.has_product_placement:
            errors.append(
                f"{prefix}: reference_transform must not require product_placement"
            )
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


def _is_scene_only(prompt: str) -> bool:
    text = _SPACE_RE.sub(" ", prompt.lower()).strip()
    for phrase in _NEGATED_DRAW:
        text = text.replace(phrase, " ")
    return not any(marker in text for marker in _PRODUCT_AS_SUBJECT)


def _add_int(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)
