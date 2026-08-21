from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.backgrounds import backgrounds_for_style
from app.content.context import pick
from app.core import messages
from app.core.errors import invalid
from app.db.models import Campaign, CampaignConcept, GenerationJob
from app.providers.vision import get_visual_planner
from app.providers.vision.base import (
    CampaignDirection,
    PlannerContext,
    PlannerResult,
    PreviousDirection,
)
from app.services.campaigns import jobs as job_records
from app.services.campaigns import queries
from app.services.campaigns.product_media import load_reference_bytes
from app.services.campaigns.recipes import recipe_from_direction


def planner_snapshot(result: PlannerResult) -> dict:
    return {
        "product_visual_analysis": result.product_visual_analysis,
        "product_type": result.product_type,
        "visual_identity": list(result.visual_identity),
        "identity_constraints": list(result.identity_constraints),
        "input_quality": {
            "status": result.input_quality.status,
            "reasons": list(result.input_quality.reasons),
        },
        "unsuitable_style_ids": list(result.unsuitable_style_ids),
        "unsuitable_template_ids": list(result.unsuitable_template_ids),
        "forbidden_claims": list(result.forbidden_claims),
    }


def direction_raw_json(
    direction: CampaignDirection, *, background_id: str
) -> dict:
    return {
        "background_id": background_id,
        "angle": direction.angle,
        "style_id": direction.style_id,
        "template_id": direction.template_id,
        "identity_constraints": list(direction.identity_constraints),
        "warning_fa": direction.warning_fa,
        "image_direction": direction.image_direction,
        "scene_direction": direction.image_direction,
        "text_safe_area": direction.text_safe_area,
    }


async def write_directions(
    session: AsyncSession,
    campaign: Campaign,
    result: PlannerResult,
) -> list[CampaignConcept]:
    await session.execute(
        delete(CampaignConcept).where(CampaignConcept.campaign_id == campaign.id)
    )
    backgrounds = backgrounds_for_style(campaign.visual_style)
    round_index = campaign.concept_round or 0
    created: list[CampaignConcept] = []
    for index, direction in enumerate(result.directions):
        background_id = pick(backgrounds, round_index + index)
        concept = CampaignConcept(
            campaign_id=campaign.id,
            concept_number=index + 1,
            title_fa=direction.title_fa,
            headline_fa=direction.headline_fa,
            description_fa=direction.description_fa,
            visual_direction=direction.visual_direction,
            background_prompt=direction.background_prompt,
            raw_json=direction_raw_json(direction, background_id=background_id),
            selected=False,
        )
        session.add(concept)
        created.append(concept)
    campaign.planner_result_json = planner_snapshot(result)
    await session.flush()
    return created


def previous_from_concepts(
    rows: list[CampaignConcept],
) -> tuple[PreviousDirection, ...]:
    previous: list[PreviousDirection] = []
    for row in rows:
        raw = row.raw_json or {}
        previous.append(
            PreviousDirection(
                title_fa=row.title_fa,
                angle=str(raw.get("angle") or row.visual_direction),
                style_id=str(raw.get("style_id") or ""),
                template_id=str(raw.get("template_id") or ""),
            )
        )
    return tuple(previous)


def is_legacy_direction(concept: CampaignConcept) -> bool:
    raw = concept.raw_json or {}
    return not raw.get("style_id")


async def plan_directions(
    session: AsyncSession, campaign: Campaign, user_id
) -> PlannerResult:
    reference, _ = await load_reference_bytes(session, campaign)
    if reference is None:
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)

    existing = await queries.concepts_of(session, campaign.id)
    ctx = await queries.build_copy_context(session, campaign)
    context = PlannerContext(
        product_name=ctx.product_name,
        description=ctx.description,
        brand_name=ctx.brand_name,
        price_text=ctx.price_text,
        audience=ctx.audience,
        objective=ctx.objective,
        visual_style=ctx.style,
        previous_directions=previous_from_concepts(existing),
    )
    planner = get_visual_planner()
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="visual_planner",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "objective": campaign.objective,
            "style": campaign.visual_style,
            "round": campaign.concept_round,
        },
    )
    session.add(job)
    await session.flush()
    try:
        result = await planner.plan_directions(reference, context)
    except Exception as error:
        job_records.mark_failed(job, error)
        raise
    job.provider = planner.name
    job.model = planner.model
    if result.usage is not None:
        job_records.apply_llm_usage(job, result.usage)
    job_records.mark_succeeded(
        job,
        {
            "product_type": result.product_type,
            "input_quality": result.input_quality.status,
            "directions": [
                {
                    "style_id": item.style_id,
                    "template_id": item.template_id,
                    "title_fa": item.title_fa,
                }
                for item in result.directions
            ],
        },
        consume_llm=False,
    )
    return result


def recipe_for_concept(
    concept: CampaignConcept, *, planner: dict | None = None
) -> dict | None:
    raw = concept.raw_json or {}
    style_id = raw.get("style_id")
    template_id = raw.get("template_id")
    if not style_id or not template_id:
        return None
    direction = CampaignDirection(
        title_fa=concept.title_fa,
        description_fa=concept.description_fa,
        angle=str(raw.get("angle") or ""),
        headline_fa=concept.headline_fa,
        visual_direction=concept.visual_direction,
        style_id=str(style_id),
        template_id=str(template_id),
        identity_constraints=tuple(raw.get("identity_constraints") or ()),
        warning_fa=str(raw.get("warning_fa") or ""),
        image_direction=str(
            raw.get("image_direction") or raw.get("scene_direction") or ""
        ),
        background_prompt=concept.background_prompt,
        text_safe_area=str(raw.get("text_safe_area") or "bottom"),
    )
    return recipe_from_direction(direction, planner=planner or {})
