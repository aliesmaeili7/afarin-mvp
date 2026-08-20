from app.content.visual_catalog import style_by_id, template_by_id
from app.core import messages
from app.core.errors import invalid
from app.providers.vision.base import RecipeProposal


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
) -> dict:
    try:
        style = style_by_id(style_id)
        template = template_by_id(template_id)
    except KeyError as error:
        raise invalid(messages.VISUAL_RECIPE_INVALID) from error
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
    }


def recipe_from_proposal(proposal: RecipeProposal, *, planner: dict) -> dict:
    return recipe_from_ids(
        proposal.style_id,
        proposal.template_id,
        source="smart",
        scene_direction=proposal.scene_direction,
        identity_constraints=list(proposal.identity_constraints),
        title_fa=proposal.title_fa,
        description_fa=proposal.description_fa,
        warning_fa=proposal.warning_fa,
        text_safe_area=proposal.text_safe_area,
        planner=planner,
    )
