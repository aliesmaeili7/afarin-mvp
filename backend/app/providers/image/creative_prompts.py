"""Prompts for creative reference-image generation.

Persian type is never requested from the image model.
CREATIVE_PROMPT_VERSION is a comparison label for eval runs.
The Unified Creative Agent writes the Seedream prompt (final_prompt).
"""

from __future__ import annotations

CREATIVE_PROMPT_VERSION = "unified_creative_agent_v1"

INVENTED_TEXT_RULE = (
    "do not invent readable text, letters, numbers, logos, or captions "
    "that are not already on the referenced product"
)

SAFETY_SUFFIX = INVENTED_TEXT_RULE


def build_repair_prompt(base: str) -> str:
    return (
        f"{base}\n\nrepair pass: keep the same recipe, fix identity and artifacts, "
        f"{INVENTED_TEXT_RULE}"
    )
