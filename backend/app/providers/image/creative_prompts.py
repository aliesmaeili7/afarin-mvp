"""Prompts for creative reference-image generation.

Accurate empty-scene prompts stay in prompts.py. Persian type is never
requested from the image model.

CREATIVE_PROMPT_VERSION is a comparison label for eval runs.
"""

from app.providers.vision.base import ArchitectCandidate, PromptArchitectResult
from app.db.models import Campaign, CampaignConcept

CREATIVE_PROMPT_VERSION = "creative_prompt_architect_v1"

SAFETY_SUFFIX = (
    "only the referenced product and this SKU, no extra variants, "
    "no readable text, no letters, no numbers, no typography, no captions, "
    "no invented logos, no Instagram or gallery UI, no pagination, "
    "no profile icons, no watermarks, no fake branding"
)


def compile_creative_prompt(
    candidate: ArchitectCandidate,
    *,
    identity_constraints: list[str] | tuple[str, ...] = (),
    text_safe_area: str = "bottom",
    extra_preserve: list[str] | tuple[str, ...] = (),
) -> str:
    preserve = [
        item
        for item in (
            *identity_constraints,
            *candidate.must_preserve,
            *extra_preserve,
        )
        if item
    ]
    avoid = [item for item in candidate.must_avoid if item]
    parts = [
        candidate.image_prompt.strip(),
        SAFETY_SUFFIX,
        f"preserve: {', '.join(preserve)}" if preserve else "",
        f"avoid: {', '.join(avoid)}" if avoid else "",
        f"leave a clear empty {text_safe_area} area for later Persian overlay type, "
        "no letters there",
        "4:5 Instagram advertisement still",
    ]
    return ", ".join(part for part in parts if part)


def compile_architect_result(
    result: PromptArchitectResult,
    *,
    identity_constraints: list[str] | tuple[str, ...] = (),
    text_safe_area: str = "bottom",
) -> PromptArchitectResult:
    compiled = []
    extra = tuple(item.feature for item in result.identity_priority if item.importance == "critical")
    for item in result.candidates:
        prompt = compile_creative_prompt(
            item,
            identity_constraints=identity_constraints,
            text_safe_area=item.composition.text_safe_area or text_safe_area,
            extra_preserve=extra,
        )
        compiled.append(
            ArchitectCandidate(
                slot=item.slot,
                intention=item.intention,
                composition=item.composition,
                lighting=item.lighting,
                palette=item.palette,
                relevant_props=item.relevant_props,
                must_preserve=item.must_preserve,
                must_avoid=item.must_avoid,
                image_prompt=item.image_prompt,
                compiled_prompt=prompt,
            )
        )
    return PromptArchitectResult(
        reference_summary=result.reference_summary,
        identity_priority=result.identity_priority,
        art_direction=result.art_direction,
        candidates=tuple(compiled),
        usage=result.usage,
        llm_trace=result.llm_trace,
    )


def build_story_prompt(
    concept: CampaignConcept | None,
    campaign: Campaign,
    recipe: dict,
) -> str:
    del campaign
    visual = (concept.visual_direction or "").strip() if concept else ""
    direction = str(recipe.get("scene_direction") or "").strip()
    return ", ".join(
        part
        for part in (
            "adapt the attached 4:5 advertising still into a 9:16 vertical story frame",
            "keep the same style, product identity, and scene",
            "extend the environment by outpainting, do not redesign the product",
            visual,
            direction,
            "leave empty space for overlay typography",
            SAFETY_SUFFIX,
        )
        if part
    )


def build_repair_prompt(base: str) -> str:
    return (
        f"{base}, repair pass: keep the same recipe, fix identity and artifacts, "
        "still no readable text"
    )


HARD_NEGATIVES = (
    "no readable text",
    "no letters",
    "no numbers",
    "no typography",
    "no captions",
    "no logos that are not on the reference product",
    "no extra product variants",
    "no watermarks",
    "no UI chrome",
    "no invented packaging claims",
)
