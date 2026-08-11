"""
Background identifiers, style by style.

Only the IDs live here. The CSS that paints each background stays in
frontend/lib/content/backgrounds.ts, because Phase 2 still composes every ad in
the browser. The backend's job is to pick an ID; the renderer resolves it.

tests/test_backgrounds_parity.py parses the TypeScript file and fails if the two
lists ever drift apart.
"""

BACKGROUNDS_BY_STYLE: dict[str, tuple[str, ...]] = {
    "luxury": ("luxury_night", "luxury_velvet"),
    "minimal": ("minimal_sand", "minimal_paper"),
    "friendly": ("friendly_peach", "friendly_cream"),
    "bold": ("bold_pop", "bold_electric"),
    "persian_traditional": ("persian_emerald", "persian_saffron"),
    "modern": ("modern_ice", "modern_slate"),
}

DEFAULT_STYLE = "modern"


def backgrounds_for_style(style: str | None) -> tuple[str, ...]:
    return (
        BACKGROUNDS_BY_STYLE.get(style or DEFAULT_STYLE)
        or BACKGROUNDS_BY_STYLE[DEFAULT_STYLE]
    )


def all_background_ids() -> set[str]:
    return {
        background
        for backgrounds in BACKGROUNDS_BY_STYLE.values()
        for background in backgrounds
    }
