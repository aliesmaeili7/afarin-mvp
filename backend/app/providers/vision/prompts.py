from app.content.visual_catalog import catalog_digest, template_ids
from app.providers.vision.base import CreativeAgentContext, QualityContext

CREATIVE_AGENT_SYSTEM = """
You are Afarin's unified Creative Agent. You SEE the seller's product photograph.
Return strict JSON only. No markdown, no chain-of-thought.

You produce everything needed for a Persian Instagram campaign in one response:
visual concepts, final image-generation prompts, on-image headlines, captions,
Story text, CTAs, and hashtags.

The JSON is for Afarin. final_prompt is the ONLY text the image model will
receive. Seedream never sees the JSON. Synthesize a short photographic
paragraph; do not dump fields, headings, bullets, or JSON into final_prompt.

final_prompt rules:
- 3–6 short sentences, one paragraph
- prefer 400–700 characters; never exceed 800
- describe the picture as a finished 4:5 Instagram advertisement still
- mention a deliberate empty region for later Persian overlay type (no letters there)
- do not invent readable text, letters, numbers, logos, captions, or extra SKUs
- never concatenate catalog copy verbatim; translate guidance into concrete
  camera, light, materials, and structure
- the cleaned reference is the product the generator will see; describe this
  exact product in the full image

Treat the uploaded seller product as the source of truth.
Never invent another SKU, package, flavor, logo, product color, or product graphic.
If the product already has text/logo/graphics, preserve them as faithfully as
the image model allows.

Do not reproduce Instagram UI, gallery UI, watermarks, or unrelated labels.

Copy rules:
- on_image_headline, on_image_secondary, feed_caption, story_text, cta: Persian
- hashtags may mix Persian and relevant English tags
- write copy from the product, brief, and creative concept
- do not mention fragile incidental visual details the image model may not
  reproduce exactly
- Seedream does not paint the Persian campaign text; that is overlaid later

Template / instruction:
- If a template is supplied, treat it as creative guidance, not a prompt fragment
- If the seller wrote a visual instruction, that instruction has priority
- If both exist, follow the instruction and use the template as extra guidance
- If neither is supplied, choose the strongest advertising approach yourself
- template_id on each image may be a catalog id or null when you chose freely

Return exactly {count} image object(s).
When count is 3, create three independently strong ad executions of the same
product and brief. They must differ meaningfully in several of: campaign angle,
composition, environment, camera relationship, product placement, human presence
or pose, lighting, visual hierarchy, and text-safe region. Do not label them
safe / editorial / bold unless that is independently useful. Suitability beats
forced gimmicks.

Anti-habit: do not default to 50mm eye-level, gray seamless, centered hero,
softbox-left / rim-right, and a bottom 15% type band unless the concept truly
wants that. Type-safe region may be upper-left, upper-right, a side band, a
wall, sky, foreground, bottom, or another intentional empty space.

identity.must_preserve must list visible product identity (silhouette, color,
graphics, materials). identity.must_not_generate lists fakes to avoid.
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


def creative_agent_system(count: int) -> str:
    return CREATIVE_AGENT_SYSTEM.format(count=count)


def creative_user_prompt(
    context: CreativeAgentContext, *, correction: str | None = None
) -> str:
    ids = ", ".join(template_ids())
    lines = [
        "CLEANED reference is the image the generator will see.",
        f"Product name: {context.product_name}",
        f"Description: {context.description or 'unknown'}",
        f"Brand: {context.brand_name or 'unknown'}",
        f"Price/promotion: {context.price_text or 'unknown'}",
        f"Audience: {context.audience or 'unknown'}",
        f"Objective: {context.objective}",
        f"Campaign mood (حس تبلیغ): {context.visual_style}",
        f"Requested image count: {context.requested_image_count}",
        f"Known template ids: {ids}",
        "Catalog semantics (guidance only, do not paste into final_prompt):",
        context.catalog_digest or catalog_digest(),
    ]
    if context.template_id:
        lines.append(f"Seller-selected template: {context.template_id}")
        if context.template_semantics:
            lines.append(f"Selected template semantics: {context.template_semantics}")
        lines.append(
            "Use this template as creative guidance unless the seller instruction "
            "overrides it."
        )
    else:
        lines.append(
            "No template selected. Choose the best advertising approach yourself."
        )
    instruction = (context.visual_instruction or "").strip()
    if instruction:
        lines.append("Seller visual instruction (priority over template):")
        lines.append(instruction)
    lines.append(
        f"Return exactly {context.requested_image_count} image object(s) "
        "with final_prompt and full Persian copy for each."
    )
    if correction:
        lines.append(correction)
    return "\n".join(lines)


def quality_user_prompt(context: QualityContext, count: int) -> str:
    return "\n".join(
        [
            f"Product: {context.product_name}",
            f"Template: {context.template_id or 'afarin_chose'}",
            "Identity constraints: "
            f"{', '.join(context.identity_constraints) or 'none'}",
            f"There are {count} candidates after the reference image.",
            "Score each candidate. Slot numbers start at 1.",
        ]
    )
