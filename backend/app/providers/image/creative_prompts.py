"""Prompts for creative reference-image generation.

Accurate empty-scene prompts stay in prompts.py. Persian type is never
requested from the image model.

CREATIVE_PROMPT_VERSION is a comparison label for eval runs.
The Prompt Architect writes the Seedream prompt (final_prompt). This module
keeps the version stamp plus story/repair wrappers — not a candidate compiler.
"""

from __future__ import annotations

from app.db.models import Campaign, CampaignConcept

CREATIVE_PROMPT_VERSION = "creative_prompt_architect_v1_2"

INVENTED_TEXT_RULE = (
    "do not invent readable text, letters, numbers, logos, or captions "
    "that are not already on the referenced product"
)

# Alias for preview scripts; no longer a global "no numbers" ban.
SAFETY_SUFFIX = INVENTED_TEXT_RULE


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
            INVENTED_TEXT_RULE,
        )
        if part
    )


def build_repair_prompt(base: str) -> str:
    return (
        f"{base}\n\nrepair pass: keep the same recipe, fix identity and artifacts, "
        f"{INVENTED_TEXT_RULE}"
    )


HARD_NEGATIVES = (
    "no readable text",
    "no letters",
    "no typography",
    "no captions",
    "no logos that are not on the reference product",
    "no extra product variants",
    "no watermarks",
    "no UI chrome",
    "no invented packaging claims",
)
