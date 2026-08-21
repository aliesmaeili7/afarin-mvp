from app.content.visual_catalog import style_by_id, template_by_id
from app.core import messages
from app.core.errors import invalid
from app.providers.vision.base import CampaignDirection


def recommended_from(recipe: dict) -> dict[str, str]:
    rec = recipe.get("recommended")
    if isinstance(rec, dict) and rec.get("style_id") and rec.get("template_id"):
        return {
            "style_id": str(rec["style_id"]),
            "template_id": str(rec["template_id"]),
        }
    style_id = recipe.get("style_id")
    template_id = recipe.get("template_id")
    if style_id and template_id:
        return {"style_id": str(style_id), "template_id": str(template_id)}
    return {}


def recipe_from_ids(
    style_id: str,
    template_id: str,
    *,
    source: str,
    scene_direction: str = "",
    identity_constraints: list[str] | None = None,
    title_fa: str | None = None,
    description_fa: str | None = None,
    warning_fa: str = "",
    text_safe_area: str | None = None,
    planner: dict | None = None,
    recommended: dict | None = None,
) -> dict:
    try:
        style = style_by_id(style_id)
        template = template_by_id(template_id)
    except KeyError as error:
        raise invalid(messages.VISUAL_RECIPE_INVALID) from error
    rec = recommended or {"style_id": style["id"], "template_id": template["id"]}
    return {
        "style_id": style["id"],
        "template_id": template["id"],
        "source": source,
        "transformation_mode": "creative",
        "scene_direction": scene_direction,
        "identity_constraints": identity_constraints or [],
        "title_fa": title_fa or style["label_fa"],
        "description_fa": description_fa or template["description_fa"],
        "warning_fa": warning_fa,
        "text_safe_area": text_safe_area
        or template.get("default_text_safe_area")
        or "bottom",
        "planner": planner or {},
        "recommended": rec,
    }


def recipe_from_direction(
    direction: CampaignDirection, *, planner: dict, source: str = "smart"
) -> dict:
    return recipe_from_ids(
        direction.style_id,
        direction.template_id,
        source=source,
        scene_direction=direction.image_direction,
        identity_constraints=list(direction.identity_constraints),
        title_fa=direction.title_fa,
        description_fa=direction.description_fa,
        warning_fa=direction.warning_fa,
        text_safe_area=direction.text_safe_area,
        planner=planner,
        recommended={
            "style_id": direction.style_id,
            "template_id": direction.template_id,
        },
    )
