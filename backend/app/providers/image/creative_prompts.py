"""Prompts for creative reference-image generation.

Accurate empty-scene prompts stay in prompts.py. Persian type is never
requested from the image model.
"""

from app.content.visual_catalog import style_by_id, template_by_id
from app.db.models import Campaign, CampaignConcept

VARIATIONS = (
    "variation A: slightly higher camera, cooler rim light, extra "
    "negative space on the type-safe side",
    "variation B: three-quarter angle, warmer key light, alternate "
    "supporting props that do not change the product",
    "variation C: closer crop or alternate pose, softer fill, "
    "different environment details in the same recipe",
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


def build_creative_prompt(
    concept: CampaignConcept | None,
    campaign: Campaign,
    recipe: dict,
    *,
    variation: int,
    identity_constraints: list[str] | tuple[str, ...] = (),
) -> str:
    style = style_by_id(str(recipe.get("style_id") or "photoreal_commercial"))
    template = template_by_id(str(recipe.get("template_id") or "hero_product"))
    visual = (concept.visual_direction or "").strip() if concept else ""
    direction = str(recipe.get("scene_direction") or "").strip()
    safe = str(
        recipe.get("text_safe_area")
        or template.get("default_text_safe_area")
        or "bottom"
    )
    constraints = list(identity_constraints) or list(
        recipe.get("identity_constraints") or []
    )
    keep = (
        ", ".join(constraints)
        if constraints
        else "keep the product recognizable from the reference"
    )
    index = variation % len(VARIATIONS)
    parts = [
        "advertising still using the attached product image as the identity reference",
        style["prompt_atoms"],
        template["prompt_atoms"],
        visual,
        direction,
        f"keep product identity: {keep}",
        f"leave a clear empty {safe} area for later typography overlay, "
        "no letters there",
        VARIATIONS[index],
        *HARD_NEGATIVES,
    ]
    mood = campaign.visual_style
    if mood:
        parts.append(f"campaign mood: {mood}")
    return ", ".join(part for part in parts if part)


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
            *HARD_NEGATIVES,
        )
        if part
    )


def build_repair_prompt(base: str) -> str:
    return (
        f"{base}, repair pass: keep the same recipe, fix identity and artifacts, "
        "still no readable text"
    )
