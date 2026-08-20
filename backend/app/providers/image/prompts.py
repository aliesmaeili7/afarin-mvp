"""
Prompts for empty campaign scenes.

The product, packaging and any lettering stay out of the image model. AdCanvas
layers the seller's pixels and Persian type on top.
"""

from app.db.models import Campaign, CampaignConcept

STYLE_ATMOSPHERE = {
    "luxury": "premium commercial photography, rich materials, cinematic lighting",
    "minimal": "clean minimal set, soft even light, generous negative space",
    "friendly": "warm inviting atmosphere, soft daylight, gentle color",
    "bold": "high contrast commercial set, saturated color, graphic lighting",
    "persian_traditional": (
        "warm traditional Persian interior atmosphere, textured fabrics, "
        "soft golden light, no ornaments with lettering"
    ),
    "modern": "contemporary commercial photography, polished surfaces, natural light",
}

HARD_NEGATIVES = (
    "empty scene only",
    "environment and lighting and atmosphere only",
    "no product",
    "no packaging",
    "no bottle",
    "no box",
    "no jar",
    "no garment on a hanger",
    "no people",
    "no hands",
    "no person holding a SKU",
    "no logos",
    "no labels",
    "no barcodes",
    "no watermarks",
    "no UI chrome",
    "no captions",
    "no typography",
    "no letters",
    "no numbers",
    "no Persian text",
    "no Arabic text",
    "no Latin text",
    "no text of any kind",
)


def build_scene_prompt(
    concept: CampaignConcept | None,
    campaign: Campaign,
    *,
    variation: int = 0,
) -> str:
    visual = (concept.visual_direction or "").strip() if concept else ""
    background = (concept.background_prompt or "").strip() if concept else ""
    style = campaign.visual_style or "modern"
    atmosphere = STYLE_ATMOSPHERE.get(style, STYLE_ATMOSPHERE["modern"])

    parts = [
        visual,
        background,
        atmosphere,
        *HARD_NEGATIVES,
        "no text",
    ]
    if variation:
        parts.append(
            f"variation {variation}, different camera angle, alternate composition"
        )
    return ", ".join(part for part in parts if part)
