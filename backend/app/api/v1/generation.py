import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import Settings
from app.core.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.enums import VISUAL_FINAL_TYPES
from app.core.errors import ApiError, generation_failed, invalid
from app.db.models import Campaign, GenerationJob
from app.db.session import get_sessionmaker
from app.providers.image import get_image_provider
from app.schemas.domain import CampaignStatusOut
from app.services.campaigns import creative as creative_visuals
from app.services.campaigns import jobs as job_records
from app.services.campaigns import queries
from app.services.campaigns.ownership import get_owned_campaign
from app.services.campaigns.stages import (
    compute_progress,
    job_stage,
    progress_for_stage,
    set_job_stage,
)

router = APIRouter(prefix="/api/campaigns", tags=["generation"])

logger = logging.getLogger(__name__)

_TERMINAL = ("ready", "partial_failed", "failed")
_VISUAL_JOBS = ("campaign_generation", "image_generation")


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

    if not campaign.objective or not campaign.visual_style:
        raise invalid(messages.BRIEF_INCOMPLETE)
    if campaign.status in ("ready", "partial_failed"):
        return _status(campaign, None, 100, None)

    active = await _active_visual_job(session, campaign.id)
    if active is not None or campaign.status in ("queued", "generating"):
        return _status(campaign, "planning", 1, messages.QUEUED)

    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="campaign_generation",
        status="queued",
        started_at=datetime.now(UTC),
        provider=None,
        model=None,
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

    session.add(
        GenerationJob(
            campaign_id=campaign.id,
            user_id=user_id,
            job_type="image_generation",
            status="queued",
            started_at=datetime.now(UTC),
            provider=None,
            model=None,
            input_json={
                "objective": campaign.objective,
                "style": campaign.visual_style,
            },
        )
    )
    try:
        await session.flush()
    except IntegrityError:
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
    background: BackgroundTasks,
) -> CampaignStatusOut:
    campaign = await get_owned_campaign(session, principal, campaign_id)

    if campaign.status in _TERMINAL:
        from app.services.campaigns import summaries

        await summaries.ensure_materialized(session, campaign)
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(
            campaign,
            None,
            0 if campaign.status == "failed" else 100,
            None,
            failed,
        )

    image_job = await _active_job_of(session, campaign.id, "image_generation")
    copy_job = await _latest_job(session, campaign.id, "campaign_generation")
    if copy_job is None or copy_job.status == "failed":
        if campaign.status not in _TERMINAL:
            return _status(campaign, None, 0, None)
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(campaign, None, 0, None, failed)

    return await _advance(
        session, campaign, copy_job, settings, image_job, background
    )


async def _advance(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    settings: Settings,
    image_job: GenerationJob | None = None,
    background: BackgroundTasks | None = None,
) -> CampaignStatusOut:
    """
    Theatre timer for stub runs, then the Creative Agent and Seedream.
    Live image jobs run in the background so the status poller can advance.
    """
    started = job.started_at or datetime.now(UTC)
    elapsed_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    if elapsed_ms < settings.generation_queue_ms:
        campaign.status = "queued"
        await session.flush()
        return _status(campaign, None, 1, messages.QUEUED)

    progress = compute_progress(
        elapsed_ms - settings.generation_queue_ms, _simulated_ms(settings)
    )

    if not progress.done:
        campaign.status = "generating"
        job.status = "processing"
        if image_job is not None and image_job.status == "queued":
            image_job.status = "processing"
        await session.flush()
        return _status(campaign, progress.stage, progress.percent, progress.message_fa)

    locked = await session.scalar(
        select(GenerationJob).where(GenerationJob.id == job.id).with_for_update()
    )
    if locked is not None and locked.status == "failed":
        await session.refresh(campaign)
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(campaign, None, 0, messages.GENERATION_FAILED, failed)

    if locked is not None and locked.status != "succeeded":
        job_records.mark_succeeded(locked)
        campaign.status = "generating"
        campaign.updated_at = datetime.now(UTC)
        await session.flush()

    image_job = image_job or await _ensure_image_job(session, campaign, job)
    locked_image = await session.scalar(
        select(GenerationJob).where(GenerationJob.id == image_job.id).with_for_update()
    )
    if locked_image is not None:
        image_job = locked_image
    live = progress_for_stage(job_stage(image_job))
    if image_job.status == "processing":
        # A live worker is already running. Never start a second one even if
        # the stage column has not been written yet.
        campaign.status = "generating"
        await session.flush()
        shown = live or progress_for_stage("planning")
        assert shown is not None
        return _status(campaign, shown.stage, shown.percent, shown.message_fa)
    if image_job.status in ("succeeded", "failed"):
        await session.refresh(campaign)
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(
            campaign,
            None,
            0 if campaign.status == "failed" else 100,
            None,
            failed,
        )

    campaign.status = "generating"
    image_job.status = "processing"
    set_job_stage(image_job, "planning")
    await session.flush()
    # Commit so a later poll can see `planning` while Seedream still runs.
    # get_session() also commits at request end; this extra commit is what
    # unblocks the progress UI for live image providers.
    await session.commit()

    if settings.image_provider != "stub" and background is not None:
        background.add_task(_run_images_background, campaign.id, image_job.id)
        started_progress = progress_for_stage("planning")
        assert started_progress is not None
        return _status(
            campaign,
            started_progress.stage,
            started_progress.percent,
            started_progress.message_fa,
        )

    return await _run_images(session, campaign, image_job)


async def _run_images_background(campaign_id: uuid.UUID, job_id: uuid.UUID) -> None:
    async with get_sessionmaker()() as session:
        try:
            campaign = await session.get(Campaign, campaign_id)
            job = await session.get(GenerationJob, job_id)
            if campaign is None or job is None:
                return
            await _run_images(session, campaign, job)
            await session.commit()
        except Exception:
            logger.exception("background image generation failed")
            await session.rollback()
            async with get_sessionmaker()() as failed:
                job = await failed.get(GenerationJob, job_id)
                campaign = await failed.get(Campaign, campaign_id)
                if job is not None and job.status not in ("succeeded", "failed"):
                    job_records.mark_image_failed(
                        job, generation_failed(), provider=get_image_provider().name
                    )
                if campaign is not None and campaign.status not in _TERMINAL:
                    campaign.status = "partial_failed"
                    campaign.updated_at = datetime.now(UTC)
                await failed.commit()


async def _run_images(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
) -> CampaignStatusOut:
    locked = await session.scalar(
        select(GenerationJob).where(GenerationJob.id == job.id).with_for_update()
    )
    if locked is not None and locked.status in ("succeeded", "failed"):
        await session.refresh(campaign)
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(
            campaign,
            None,
            0 if campaign.status == "failed" else 100,
            None,
            failed,
        )

    campaign.status = "generating"
    if locked is not None:
        locked.status = "processing"
    await session.flush()

    provider_name = get_image_provider().name
    try:
        await creative_visuals.generate_candidates(
            session, campaign, locked or job, source="smart"
        )
        usage = None
        failures: list[dict] = []
    except Exception as error:
        logger.exception("creative image generation failed")
        if locked is not None:
            job_records.mark_image_failed(locked, error, provider=provider_name)
        if isinstance(error, ApiError) and error.message_fa in (
            messages.INPUT_QUALITY_NEEDS_FIX,
            messages.CREATIVE_ATTEMPTS_EXHAUSTED,
        ):
            campaign.status = "brief_complete"
        else:
            campaign.status = "partial_failed"
            await _mark_finals_failed(session, campaign.id)
        campaign.updated_at = datetime.now(UTC)
        await session.flush()
        message = (
            error.message_fa
            if isinstance(error, ApiError)
            else messages.GENERATION_FAILED
        )
        failed = await queries.failed_visual_types(session, campaign.id)
        return _status(campaign, None, 0, message, failed)

    image_output = {"image_errors": failures} if failures else None
    if locked is not None:
        output = dict(locked.input_json or {})
        if image_output:
            output.update(image_output)
        job_records.mark_image_succeeded(
            locked, usage, provider=provider_name, output=output
        )
        campaign.status = "ready"

    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    failed = await queries.failed_visual_types(session, campaign.id)
    return _status(campaign, None, 100, None, failed)


async def _ensure_image_job(
    session: AsyncSession, campaign: Campaign, copy_job: GenerationJob
) -> GenerationJob:
    existing = await _latest_job(session, campaign.id, "image_generation")
    if existing is not None and existing.status in ("queued", "processing"):
        return existing

    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=copy_job.user_id,
        job_type="image_generation",
        status="queued",
        started_at=datetime.now(UTC),
        provider=None,
        model=None,
        input_json={"objective": campaign.objective, "style": campaign.visual_style},
    )
    session.add(job)
    await session.flush()
    return job


async def _mark_finals_failed(session: AsyncSession, campaign_id: uuid.UUID) -> None:
    for asset in await queries.assets_of(session, campaign_id):
        if asset.asset_type not in VISUAL_FINAL_TYPES:
            continue
        spec = dict(asset.metadata_json or {})
        spec["failed"] = True
        asset.metadata_json = spec


def _simulated_ms(settings: Settings) -> int:
    # Real image latency should not sit on top of the Phase 1 theatre timer.
    if settings.image_provider != "stub":
        return 0
    return settings.generation_simulated_ms


async def _active_visual_job(
    session: AsyncSession, campaign_id: uuid.UUID
) -> GenerationJob | None:
    return await session.scalar(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign_id,
            GenerationJob.job_type.in_(_VISUAL_JOBS),
            GenerationJob.status.in_(("queued", "processing")),
        )
    )


async def _active_job_of(
    session: AsyncSession, campaign_id: uuid.UUID, job_type: str
) -> GenerationJob | None:
    return await session.scalar(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign_id,
            GenerationJob.job_type == job_type,
            GenerationJob.status.in_(("queued", "processing")),
        )
    )


async def _latest_job(
    session: AsyncSession, campaign_id: uuid.UUID, job_type: str
) -> GenerationJob | None:
    return await session.scalar(
        select(GenerationJob)
        .where(
            GenerationJob.campaign_id == campaign_id,
            GenerationJob.job_type == job_type,
        )
        .order_by(GenerationJob.started_at.desc())
        .limit(1)
    )
