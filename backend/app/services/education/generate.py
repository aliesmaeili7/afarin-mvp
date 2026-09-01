"""
Runs one educational post and records what it cost.

Two `generation_jobs` rows are written per run, `educational_agent` and
`educational_image`, so educational spend sits in the same table as advertising
spend and the two can be compared with one query. Wall time is measured once
across the whole run rather than summed from provider latencies.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import EducationalPost, GenerationJob
from app.providers.image import get_image_provider
from app.services.campaigns import jobs as job_records
from app.services.education import core
from app.services.education.render_spec import build_render_spec
from app.services.education.themes import theme_from_agent
from app.services.storage import StorageRef, education_image_key, get_storage

logger = logging.getLogger(__name__)

AGENT_JOB = "educational_agent"
IMAGE_JOB = "educational_image"


async def run_generation(session: AsyncSession, post: EducationalPost) -> None:
    """
    prompt -> agent -> validate -> one image. No overlay spec.

    Any failure leaves the post `failed` with a Persian message and no partial
    image, because the agent is fully validated before an image is requested.
    """
    timer = core.TimedRun.start()
    post.status = "generating"
    post.updated_at = datetime.now(UTC)
    await session.flush()

    selected_theme = post.theme_json or None
    agent_job = await _open_job(
        session, post, AGENT_JOB, {"aspect": core.EDUCATION_ASPECT}
    )

    try:
        planned = await core.plan_validated_post(
            user_prompt=post.user_prompt, selected_theme=selected_theme
        )
    except Exception as error:
        _fail_agent_job(agent_job, error)
        await _fail(session, post, error, timer)
        raise

    result = planned.result
    if result.usage is not None:
        job_records.apply_llm_usage(agent_job, result.usage)
    agent_job.provider = _agent_provider_name()
    if agent_job.model is None:
        agent_job.model = _agent_model_name()
    job_records.mark_succeeded(
        agent_job,
        {
            "language": result.language,
            "final_prompt_chars": len(result.final_prompt),
            "retry_used": planned.retry_used,
        },
        consume_llm=False,
    )

    # The effective theme: a selected one wins, otherwise the agent's design.
    effective_theme = selected_theme or theme_from_agent(result.theme)

    image_job = await _open_job(
        session,
        post,
        IMAGE_JOB,
        {
            "aspect": core.EDUCATION_ASPECT,
            "n": core.EDUCATION_IMAGE_COUNT,
            "output_count": core.EDUCATION_IMAGE_COUNT,
            "model": get_settings().educational_image_model_resolved,
        },
    )
    provider_name = get_image_provider().name
    try:
        image = await core.generate_post_image(result.final_prompt)
    except Exception as error:
        job_records.mark_image_failed(image_job, error, provider=provider_name)
        await _fail(session, post, error, timer)
        raise

    path = await _store_image(post.id, image.content)
    job_records.mark_image_succeeded(
        image_job,
        image.result.usage,
        provider=provider_name,
        output={"output_count": core.EDUCATION_IMAGE_COUNT, "storage_path": path},
    )

    post.agent_json = planned.as_dict()
    post.theme_json = effective_theme
    post.language = result.language
    post.headline = core.listing_title(post.user_prompt)
    post.image_storage_path = path
    post.render_spec_json = build_render_spec(image_path=path)
    post.status = "ready"
    post.error_message = None
    post.wall_time_ms = timer.elapsed_ms()
    post.updated_at = datetime.now(UTC)
    await session.flush()


async def _store_image(post_id: uuid.UUID, content: bytes) -> str:
    settings = get_settings()
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=education_image_key(post_id, uuid.uuid4().hex[:12]),
    )
    await get_storage().upload(ref, content, "image/jpeg")
    return ref.to_path()


async def _open_job(
    session: AsyncSession,
    post: EducationalPost,
    job_type: str,
    input_json: dict,
) -> GenerationJob:
    existing = await session.scalar(
        select(GenerationJob).where(
            GenerationJob.educational_post_id == post.id,
            GenerationJob.job_type == job_type,
            GenerationJob.status.in_(("queued", "processing")),
        )
    )
    if existing is not None:
        existing.status = "processing"
        await session.flush()
        return existing
    job = GenerationJob(
        educational_post_id=post.id,
        user_id=post.user_id,
        job_type=job_type,
        status="processing",
        started_at=datetime.now(UTC),
        input_json=input_json,
    )
    session.add(job)
    await session.flush()
    return job


async def _fail(
    session: AsyncSession,
    post: EducationalPost,
    error: Exception,
    timer: core.TimedRun,
) -> None:
    post.status = "failed"
    post.error_message = (
        error.message_fa if isinstance(error, ApiError) else str(error)[:500]
    )
    post.wall_time_ms = timer.elapsed_ms()
    post.updated_at = datetime.now(UTC)
    await session.flush()


def _fail_agent_job(job: GenerationJob, error: Exception) -> None:
    """
    Deliberately not job_records.mark_failed: that consumes usage from the
    advertising content provider, which never ran here.
    """
    job.status = "failed"
    job.completed_at = datetime.now(UTC)
    job.error_message = str(error)[:2000]
    job.provider = _agent_provider_name()
    job.model = _agent_model_name()


def _agent_provider_name() -> str:
    from app.providers.education import get_educational_agent

    return get_educational_agent().name


def _agent_model_name() -> str | None:
    from app.providers.education import get_educational_agent

    return get_educational_agent().model
