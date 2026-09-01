"""
Domain value sets.

These mirror the TypeScript unions in frontend/types/domain.ts one for one.
They are stored as `text` with CHECK constraints rather than native PostgreSQL
enums because Phases 3-5 extend `asset_type` and `copy_type`, and editing a
check is cheaper than ALTER TYPE.
"""

CAMPAIGN_OBJECTIVES = (
    "sell_product",
    "new_product",
    "promotion",
    "brand_awareness",
)

VISUAL_STYLES = (
    "luxury",
    "minimal",
    "friendly",
    "bold",
    "persian_traditional",
    "modern",
)

CAMPAIGN_STATUSES = (
    "draft",
    "brief_complete",
    "concepts_ready",
    "concept_selected",
    "queued",
    "generating",
    "candidates_ready",
    "ready",
    "partial_failed",
    "failed",
)

COPY_TYPES = (
    "caption_short",
    "caption_friendly",
    "caption_persuasive",
    "story",
    "cta",
    "hashtags",
    "reel_concept",
)

ASSET_TYPES = (
    "uploaded_product",
    "product_cutout",
    "generated_background",
    "feed_final",
    "story_final",
    "carousel_1",
    "carousel_2",
    "carousel_3",
)

BRAND_ASSET_TYPES = ("logo", "reference_image", "product_reference")

JOB_STATUSES = ("queued", "processing", "succeeded", "failed", "cancelled")

JOB_TYPES = (
    "campaign_generation",
    "concept_generation",
    "copy_rewrite",
    "image_generation",
    "visual_planner",
    "prompt_architect",
    "creative_agent",
    "visual_quality_check",
    "educational_agent",
    "educational_image",
)

VISUAL_CREATION_MODES = ("accurate", "creative")

VISUAL_ATTEMPT_SOURCES = ("smart", "custom")

VISUAL_ATTEMPT_STATUSES = (
    "generating",
    "awaiting_selection",
    "selected",
    "superseded",
)

VISUAL_CANDIDATE_KINDS = ("primary", "repair")

IMAGE_OUTPUT_ROLES = ("candidate", "repair")

VISUAL_FINAL_TYPES = (
    "feed_final",
    "story_final",
    "carousel_1",
    "carousel_2",
    "carousel_3",
)

FEED_SCENE_TYPES = ("feed_final", "carousel_1", "carousel_2", "carousel_3")
STORY_SCENE_TYPES = ("story_final",)

REWRITE_INTENTS = (
    "informal",
    "shorter",
    "stronger_cta",
    "new_headline",
    "more_luxury",
)

COPY_REWRITE_INTENTS = ("informal", "shorter", "stronger_cta", "more_luxury")
ASSET_REWRITE_INTENTS = ("new_headline", "stronger_cta")

GENERATION_STAGES = ("planning", "visual", "finalizing")


# --- Educational content ---------------------------------------------------
#
# The educational path is authenticated-only and has its own small vocabulary.
# These are separate from the advertising sets on purpose: an educational post
# has no objective, no visual style and no product.

EDUCATIONAL_POST_STATUSES = ("queued", "generating", "ready", "failed")

EDUCATION_THEME_SOURCES = ("builtin", "user")

EDUCATION_LANGUAGES = ("fa", "en")


# --- Chat persistence (Phase B) --------------------------------------------
#
# A generic conversation domain, not a campaign and not an educational post.
# Artifact types include future media so the CHECK does not have to be rewritten
# when Phase C/E adds them; Phase B only writes `image`.

CHAT_LANGUAGES = ("fa", "en")
CHAT_ROLES = ("user", "assistant")
CHAT_ARTIFACT_TYPES = ("image", "audio", "video", "subtitle", "document")
CHAT_ARTIFACT_STATUSES = ("generating", "ready", "failed")
CHAT_ARTIFACT_ASPECTS = ("1:1", "4:5", "9:16")
CHAT_SKILL_HINTS = ("advertising", "education", "general_image")


def sql_in(values: tuple[str, ...]) -> str:
    """Renders a value tuple as a SQL IN list for CHECK constraints."""
    return ", ".join(f"'{value}'" for value in values)
