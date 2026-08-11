import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import Settings
from app.core.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.errors import invalid
from app.db.models import Campaign, GenerationJob
from app.schemas.domain import CampaignStatusOut
from app.services.campaigns import materialize as materializer
from app.services.campaigns.ownership import get_owned_campaign
from app.services.campaigns.stages import compute_progress

router = APIRouter(prefix="/api/campaigns", tags=["generation"])

_TERMINAL = ("ready", "partial_failed", "failed")


def _status(
    campaign: Campaign,
    stage: str | None,
    percent: int,
    message_fa: str | None,
    failed_asset_types: list[str] | None = None,
) -> CampaignStatusOut:
    return CampaignStatusOut(
        campaign_id=campaign.id,
        status=campaign.status,
        stage=stage,
        percent=percent,
        message_fa=message_fa,
        failed_asset_types=failed_asset_types or [],
    )


@router.post("/{campaign_id}/generate", response_model=CampaignStatusOut)
async def start_generation(
    campaign_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignStatusOut:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    user_id = principal.require_user()

    if campaign.selected_concept_id is None:
        raise invalid(messages.CONCEPT_REQUIRED)

    if campaign.status in ("ready", "partial_failed"):
        return _status(campaign, None, 100, None)

    active = await _active_job(session, campaign.id)
    if active is not None or campaign.status in ("queued", "generating"):
        return _status(campaign, "planning", 1, messages.QUEUED)

    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="campaign_generation",
        status="queued",
        started_at=datetime.now(UTC),
        input_json={"objective": campaign.objective, "style": campaign.visual_style},
    )
    session.add(job)
    try:
        await session.flush()
    except IntegrityError:
        # The partial unique index rejected a second concurrent job. Repeated
        # taps on «ساخت کمپین» must never launch two (spec §27).
        await session.rollback()
        refreshed = await get_owned_campaign(session, principal, campaign_id)
        return _status(refreshed, "planning", 1, messages.QUEUED)

    campaign.status = "queued"
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return _status(campaign, None, 0, messages.QUEUED)


@router.get("/{campaign_id}/status", response_model=CampaignStatusOut)
async def get_campaign_status(
    campaign_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
) -> CampaignStatusOut:
    campaign = await get_owned_campaign(session, principal, campaign_id)

    if campaign.status in _TERMINAL:
        from app.services.campaigns import summaries

        await summaries.ensure_materialized(session, campaign)
        return _status(
            campaign,
            None,
            0 if campaign.status == "failed" else 100,
            None,
            ["story_final"] if campaign.status == "partial_failed" else [],
        )

    job = await _latest_job(session, campaign.id)
    if job is None or job.status == "succeeded":
        return _status(campaign, None, 0, None)

    return await _advance(session, campaign, job, settings)


async def _advance(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    settings: Settings,
) -> CampaignStatusOut:
    """
    Derives progress from the job's start time and materializes once it elapses.

    Phase 2 has no providers, so the elapsed time is simulated; the polling
    contract is real, which is what lets Phase 4 drop a worker in behind it.
    """
    started = job.started_at or datetime.now(UTC)
    elapsed_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    if elapsed_ms < settings.generation_queue_ms:
        campaign.status = "queued"
        await session.flush()
        return _status(campaign, None, 1, messages.QUEUED)

    progress = compute_progress(
        elapsed_ms - settings.generation_queue_ms, settings.generation_simulated_ms
    )

    if not progress.done:
        campaign.status = "generating"
        job.status = "processing"
        await session.flush()
        return _status(campaign, progress.stage, progress.percent, progress.message_fa)

    # Lock the job so two concurrent polls cannot both materialize.
    locked = await session.scalar(
        select(GenerationJob).where(GenerationJob.id == job.id).with_for_update()
    )
    if locked is not None and locked.status == "succeeded":
        await session.refresh(campaign)
        return _status(campaign, None, 100, None)

    if locked is not None:
        locked.status = "succeeded"
        locked.completed_at = datetime.now(UTC)

    final_status = await materializer.materialize(session, campaign)
    campaign.updated_at = datetime.now(UTC)
    await session.flush()

    return _status(
        campaign,
        None,
        100,
        None,
        ["story_final"] if final_status == "partial_failed" else [],
    )


async def _active_job(
    session: AsyncSession, campaign_id: uuid.UUID
) -> GenerationJob | None:
    return await session.scalar(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign_id,
            GenerationJob.status.in_(("queued", "processing")),
        )
    )


async def _latest_job(
    session: AsyncSession, campaign_id: uuid.UUID
) -> GenerationJob | None:
    return await session.scalar(
        select(GenerationJob)
        .where(GenerationJob.campaign_id == campaign_id)
        .order_by(GenerationJob.started_at.desc())
        .limit(1)
    )
