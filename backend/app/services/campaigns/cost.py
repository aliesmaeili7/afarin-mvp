"""Hard caps on paid creative image outputs, counted per generated image."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import get_settings
from app.core.errors import conflict, invalid
from app.db.models import Campaign, CampaignVisualAttempt, GenerationJob

CANDIDATES_PER_ATTEMPT = 3
REPAIRS_PER_ATTEMPT = 1
STORIES_PER_ATTEMPT = 1
AUTO_OUTPUT_CEILING = 5


def output_count_of(job: GenerationJob) -> int:
    payload = job.output_json or job.input_json or {}
    raw = payload.get("output_count")
    if isinstance(raw, int) and raw > 0:
        return raw
    raw = (job.input_json or {}).get("n")
    if isinstance(raw, int) and raw > 0:
        return raw
    return 1


async def count_outputs(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    *,
    attempt_number: int | None = None,
    role: str | None = None,
) -> int:
    rows = await session.scalars(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign_id,
            GenerationJob.job_type == "image_generation",
            GenerationJob.status.in_(("succeeded", "processing")),
        )
    )
    total = 0
    for job in rows:
        data = job.input_json or {}
        if data.get("mode") != "creative":
            continue
        if attempt_number is not None and data.get("attempt_number") != attempt_number:
            continue
        if role is not None:
            counts = data.get("output_counts")
            if isinstance(counts, dict) and isinstance(counts.get(role), int):
                total += counts[role]
                continue
            if data.get("role") != role:
                continue
        total += output_count_of(job)
    return total


async def attempt_count(session: AsyncSession, campaign_id: uuid.UUID) -> int:
    rows = await session.scalars(
        select(CampaignVisualAttempt).where(
            CampaignVisualAttempt.campaign_id == campaign_id
        )
    )
    return len(list(rows))


async def assert_can_start_attempt(
    session: AsyncSession, campaign: Campaign
) -> None:
    settings = get_settings()
    used = await attempt_count(session, campaign.id)
    if used >= settings.max_creative_attempts_per_campaign:
        raise conflict(messages.CREATIVE_ATTEMPTS_EXHAUSTED)


def assert_role_budget(role: str, already: int, adding: int) -> None:
    limits = {
        "candidate": CANDIDATES_PER_ATTEMPT,
        "repair": REPAIRS_PER_ATTEMPT,
        "story_adaptation": STORIES_PER_ATTEMPT,
    }
    limit = limits.get(role)
    if limit is None:
        raise invalid(messages.GENERIC)
    if already + adding > limit:
        raise conflict(messages.CREATIVE_BUSY)


async def assert_auto_ceiling(
    session: AsyncSession, campaign_id: uuid.UUID, attempt_number: int, adding: int
) -> None:
    used = await count_outputs(
        session, campaign_id, attempt_number=attempt_number
    )
    if used + adding > AUTO_OUTPUT_CEILING:
        raise conflict(messages.CREATIVE_BUSY)
