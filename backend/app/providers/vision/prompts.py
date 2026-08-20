from app.content.visual_catalog import public_catalog, style_ids, template_ids
from app.providers.vision.base import PlannerContext

PLANNER_SYSTEM = """
You are Afarin's visual planner. You SEE the cropped product photo.
Return strict JSON only.

Rules:
- Describe only what is visible or stated in the brief.
- Never invent product claims, extra variants, prices, ingredients, or logos.
- Recommend exactly three recipes with different creative strategies:
  1) realistic/editorial  2) stylized/illustrated  3) conceptual/surreal.
- style_id must be one of: {styles}
- template_id must be one of: {templates}
- If the crop is a screenshot with UI chrome, the product is tiny, several
  products compete, or the subject is clipped, set input_quality.status to
  needs_fix.
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
    return "\n".join(
        [
            f"Product name: {context.product_name}",
            f"Description: {context.description or 'unknown'}",
            f"Brand: {context.brand_name or 'unknown'}",
            f"Price/promotion: {context.price_text or 'unknown'}",
            f"Audience: {context.audience or 'unknown'}",
            f"Objective: {context.objective}",
            f"Campaign mood: {context.visual_style}",
            f"Selected concept title: {context.concept_title_fa}",
            f"Headline: {context.concept_headline_fa}",
            f"Visual direction: {context.concept_visual_direction}",
            f"Allowed style_id values: {styles}",
            f"Allowed template_id values: {templates}",
            "Analyze the attached crop. Do not invent facts.",
        ]
    )


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
