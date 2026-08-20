from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.errors import invalid
from app.db.models import Campaign, GenerationJob
from app.providers.vision import get_visual_planner
from app.providers.vision.base import PlannerContext, PlannerResult
from app.services.campaigns import jobs as job_records
from app.services.campaigns import queries
from app.services.campaigns.product_media import load_reference_bytes
from app.services.campaigns.recipes import recipe_from_proposal


async def propose_recipes(
    session: AsyncSession, campaign: Campaign, user_id
) -> PlannerResult:
    if campaign.selected_concept_id is None:
        raise invalid(messages.CONCEPT_REQUIRED)
    reference, _ = await load_reference_bytes(session, campaign)
    if reference is None:
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)

    concept = None
    for item in await queries.concepts_of(session, campaign.id):
        if item.id == campaign.selected_concept_id:
            concept = item
            break
    ctx = await queries.build_copy_context(session, campaign)
    context = PlannerContext(
        product_name=ctx.product_name,
        description=ctx.description,
        brand_name=ctx.brand_name,
        price_text=ctx.price_text,
        audience=ctx.audience,
        objective=ctx.objective,
        visual_style=ctx.style,
        concept_title_fa=concept.title_fa if concept else "",
        concept_headline_fa=concept.headline_fa if concept else "",
        concept_visual_direction=concept.visual_direction if concept else "",
    )
    planner = get_visual_planner()
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="visual_planner",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={"objective": campaign.objective, "style": campaign.visual_style},
    )
    session.add(job)
    await session.flush()
    try:
        result = await planner.plan_recipes(reference, context)
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
            "recipes": [
                {
                    "style_id": item.style_id,
                    "template_id": item.template_id,
                    "title_fa": item.title_fa,
                }
                for item in result.recommended_recipes
            ],
        },
        consume_llm=False,
    )
    return result


def public_proposals(result: PlannerResult) -> list[dict]:
    planner_snapshot = {
        "product_type": result.product_type,
        "visual_identity": list(result.visual_identity),
        "identity_constraints": list(result.identity_constraints),
        "input_quality": {
            "status": result.input_quality.status,
            "reasons": list(result.input_quality.reasons),
        },
        "unsuitable_style_ids": list(result.unsuitable_style_ids),
        "unsuitable_template_ids": list(result.unsuitable_template_ids),
    }
    return [
        recipe_from_proposal(item, planner=planner_snapshot)
        for item in result.recommended_recipes
    ]
