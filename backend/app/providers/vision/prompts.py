from app.content.visual_catalog import (
    catalog_digest,
    selected_semantics,
    style_ids,
    template_ids,
)
from app.providers.vision.base import ArchitectContext, PlannerContext

PLANNER_SYSTEM = """
You are Afarin's Creative Director. You SEE the product photograph(s).
Return strict JSON only.

You propose exactly three complete campaign directions the seller can choose
from. Each direction already contains the strategic concept AND a visual recipe.

Rules:
- Describe only what is visible or stated in the brief.
- Never invent product claims, extra variants, prices, ingredients, or logos.
- title_fa, description_fa, headline_fa, visual_direction, warning_fa: Persian.
- angle, image_direction, background_prompt: English.
- headline_fa is a short Instagram hook, not a full caption pack.
- Do not write captions, hashtags, CTAs, or Reel scripts.
- Return exactly three materially different strategic AND visual directions
  chosen from combinations that are strong for THIS product.
- Suitability beats forced diversity. Do not auto-pick surreal as a third
  direction for cosmetics or food just to look varied.
- Prefer style×template pairings rated preferred, then allowed.
  Use a discouraged pairing only with a concrete product-specific reason
  in warning_fa, and set compatibility accordingly.
- Respect the campaign mood (حس تبلیغ) and objective.
- style_id must be one of: {styles}
- template_id must be one of: {templates}
- background_prompt is an empty-scene English prompt (environment/light only,
  include "no text") used if the seller later chooses accurate/composite mode.
- image_direction is English scene fuel for this product.
- Fill reference_analysis from what you see. Coordinates are normalized 0–1
  relative to the ORIGINAL upload when that image is attached, otherwise the
  approved crop. Bounding boxes are approximate; leave has_recommended_crop
  false unless a tighter box would clearly remove peripheral UI.
- If UI/watermark overlaps the product, the product is tiny or ambiguous,
  several products compete, the brief describes a different product, or a crop
  would destroy identity: reference_strategy=needs_user_action,
  input_quality.status=needs_fix, and still return three placeholder directions.
- For apparel/jewellery on a person, food on a plate, or useful lifestyle
  context: preserve_context_crop, never subject_cutout_neutral.
- Isolatable packaged objects without useful context may use subject_cutout_neutral.
- forbidden_claims stays empty unless the brief already states a fact.
""".strip()

QUALITY_SYSTEM = """
You are checking advertising stills against a product reference photo.
Images arrive in order: reference first, then candidate 1, candidate 2, ...
Return strict JSON only.

Hard fail a candidate when:
- the product is unrecognizable versus the reference
- there is random readable text, extra logos, or watermarks
- anatomy or artifacts are severe
- composition is clearly unusable as an ad

Also return 1–5 integer soft scores for identity_quality, style_adherence,
template_adherence, composition_quality, visual_attractiveness,
commercial_usefulness, and text_safe_space_quality.
Soft taste differences are not hard fails.
Do not invent product claims.
""".strip()

ARCHITECT_SYSTEM = """
You are Afarin's senior advertising art director and image-prompt architect.

You design three production-ready visual executions for ONE selected campaign
direction and ONE real seller product. You SEE the product/reference image(s).

Return strict JSON only. No markdown, no chain-of-thought.

The JSON is a spec for inspection, compositing, and eval.
final_prompt is the ONLY text the image model will receive. Seedream never sees
the JSON. Synthesize a short photographic paragraph; do not dump fields, headings,
bullets, or JSON into final_prompt.

final_prompt rules:
- 3–6 short sentences, one paragraph
- prefer 400–700 characters; never exceed 800
- describe the picture as a finished 4:5 Instagram advertisement still
- mention a deliberate empty region for later Persian overlay type (no letters there)
- do not invent readable text, letters, numbers, logos, captions, or extra SKUs
- never concatenate style or template catalog copy verbatim; translate it into
  concrete camera, light, materials, and structure

Treat the uploaded seller product as the source of truth.
Never invent another SKU, package, flavor, logo, product color, or product graphic.
If the product already has text/logo/graphics, preserve them as faithfully as the
image model allows.

Do not reproduce Instagram UI, gallery UI, watermarks, or unrelated labels.

Anti-habit: do not default to 50mm eye-level, gray seamless, centered hero,
softbox-left / rim-right, and a bottom 15% type band unless this direction
truly wants that. Type-safe region may be upper-left, upper-right, a side
band, a wall, sky, foreground, bottom, or another intentional empty space.

Create THREE candidates for the same selected direction that differ in several
structural axes: camera relationship, product placement, environment, pose or
geometry, lighting motivation, visual hierarchy, and type-safe region.
Bold means a stronger commercial reading of the same direction — not silly,
not a different campaign.

Candidate A / slot 1 / intention=safe: clearest commercial execution.
Candidate B / slot 2 / intention=editorial: stronger editorial composition,
still usable as an ad.
Candidate C / slot 3 / intention=bold: boldest reading allowed by the
selected style and template.

If render_strategy is preserved_product_composite:
- final_prompt describes an EMPTY scene only
- do not draw the product, package, bottle, garment, or SKU
- leave a plausible empty contact region whose perspective can accept a real
  product cutout
- fill product_placement (normalized 0–1, width as a fraction of frame width)
  and set has_product_placement true only when that integration is plausible
- prefer a modest commercial camera (eye-level or slight three-quarter);
  overhead only when the template is flat_lay

If render_strategy is reference_transform:
- the cleaned image is the product the generator will see
- final_prompt describes the FULL image including this exact product
- set has_product_placement false and product_placement to zeros

Every candidate.render_strategy must match the supplied render_strategy.
output.aspect_ratio must be 4:5.
""".strip()


def plan_user_prompt(context: PlannerContext) -> str:
    lines = [
        f"Product name: {context.product_name}",
        f"Description: {context.description or 'unknown'}",
        f"Brand: {context.brand_name or 'unknown'}",
        f"Price/promotion: {context.price_text or 'unknown'}",
        f"Audience: {context.audience or 'unknown'}",
        f"Objective: {context.objective}",
        f"Campaign mood: {context.visual_style}",
        f"Current approved crop (original 0-1): {context.crop_json or 'unknown'}",
        "Catalog semantics:",
        catalog_digest(),
        "Analyze the attached image(s). CLEANED/CROP is the approved product crop.",
        "If ORIGINAL is attached, use it only to detect UI/contamination and to "
        "propose recommended_crop in original-image coordinates.",
        "Do not invent facts.",
        "Return exactly three complete campaign directions that fit THIS product.",
    ]
    if context.previous_directions:
        lines.append(
            "The seller already saw these directions. Do not paraphrase them. "
            "Change both the strategic angle and the style/template pairing:"
        )
        for index, item in enumerate(context.previous_directions, start=1):
            lines.append(
                f"{index}. {item.title_fa} | angle={item.angle} | "
                f"{item.style_id} x {item.template_id}"
            )
    return "\n".join(lines)


def quality_user_prompt(context: PlannerContext, count: int) -> str:
    recipe = context.recipe or {}
    return "\n".join(
        [
            f"Product: {context.product_name}",
            f"Style: {recipe.get('style_id', '')}",
            f"Template: {recipe.get('template_id', '')}",
            "Identity constraints: "
            f"{', '.join(context.recipe.get('identity_constraints') or [])}",
            f"There are {count} candidates after the reference image.",
            "Score each candidate. Slot numbers start at 1.",
        ]
    )


def architect_user_prompt(
    context: ArchitectContext, *, correction: str | None = None
) -> str:
    semantics = selected_semantics(
        str(context.recipe.get("style_id") or "photoreal_commercial"),
        str(context.recipe.get("template_id") or "hero_product"),
    )
    style = context.style_semantics or semantics["style"]
    template = context.template_semantics or semantics["template"]
    preserved = context.render_strategy == "preserved_product_composite"
    lines = [
        "CLEANED reference is the image the generator will see. "
        "DIRTY/ORIGINAL if attached is context only — do not reproduce UI.",
        f"Product name: {context.product_name}",
        f"Description: {context.description or 'unknown'}",
        f"Brand: {context.brand_name or 'unknown'}",
        f"Audience: {context.audience or 'unknown'}",
        f"Objective: {context.objective}",
        f"Campaign mood: {context.visual_style}",
        f"Direction title: {context.concept_title_fa or 'n/a'}",
        f"Visual direction: {context.concept_visual_direction or 'n/a'}",
        f"Selected style: {context.recipe.get('style_id')}",
        f"Selected template: {context.recipe.get('template_id')}",
        f"Compatibility: {context.compatibility}",
        f"Text safe area hint: {context.text_safe_area}",
        f"Identity constraints: {', '.join(context.identity_constraints) or 'none'}",
        f"Reference analysis: {context.reference_analysis}",
        "Style semantics (guidance, do not paste into final_prompt):",
        str(style),
        "Template semantics (guidance, do not paste into final_prompt):",
        str(template),
        f"Render strategy: {context.render_strategy}",
        (
            "Design an empty scene with a plausible contact surface. "
            "final_prompt must not draw the product. Fill product_placement and set "
            "has_product_placement true only if a real cutout can sit there."
            if preserved
            else "The cleaned reference is the product Seedream will see. "
            "final_prompt must describe this exact product in the full image. "
            "Set has_product_placement false and product_placement zeros."
        ),
        "Return three structurally different candidates for this one recipe.",
        "Each final_prompt is a short paragraph the image model receives unchanged.",
    ]
    if correction:
        lines.append(correction)
    return "\n".join(lines)


def planner_system() -> str:
    return PLANNER_SYSTEM.format(
        styles=", ".join(style_ids()),
        templates=", ".join(template_ids()),
    )
