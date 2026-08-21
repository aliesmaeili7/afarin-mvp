from app.content.visual_catalog import public_catalog, style_ids, template_ids
from app.providers.vision.base import PlannerContext

PLANNER_SYSTEM = """
You are Afarin's Creative Director. You SEE the cropped product photo.
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
- The three directions must be materially different strategically AND visually.
  Prefer diversity such as:
  1) realistic/editorial  2) stylized/illustrated  3) conceptual/surreal
  when those fit the product. Do not return three cinematic-hero variants.
- Respect the campaign mood (حس تبلیغ) and objective.
- style_id must be one of: {styles}
- template_id must be one of: {templates}
- background_prompt is an empty-scene English prompt (environment/light only,
  include "no text") used if the seller later chooses accurate/composite mode.
- image_direction is English prompt fuel for a creative still of this product.
- If the crop is a screenshot with UI chrome, the product is tiny, several
  products compete, or the subject is clipped, set input_quality.status to
  needs_fix and still return three placeholder directions.
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

Soft taste differences are not hard fails.
Do not invent product claims.
""".strip()


def plan_user_prompt(context: PlannerContext) -> str:
    catalog = public_catalog()
    styles = ", ".join(item["id"] for item in catalog["styles"])
    templates = ", ".join(item["id"] for item in catalog["templates"])
    lines = [
        f"Product name: {context.product_name}",
        f"Description: {context.description or 'unknown'}",
        f"Brand: {context.brand_name or 'unknown'}",
        f"Price/promotion: {context.price_text or 'unknown'}",
        f"Audience: {context.audience or 'unknown'}",
        f"Objective: {context.objective}",
        f"Campaign mood: {context.visual_style}",
        f"Allowed style_id values: {styles}",
        f"Allowed template_id values: {templates}",
        "Analyze the attached crop. Do not invent facts.",
        "Return exactly three complete campaign directions.",
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


def planner_system() -> str:
    return PLANNER_SYSTEM.format(
        styles=", ".join(style_ids()),
        templates=", ".join(template_ids()),
    )
