"""Job lifecycle: idempotent start, staged progress, one materialization."""

import uuid
from collections import Counter

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.enums import VISUAL_FINAL_TYPES
from app.db.models import CampaignAsset, GenerationJob
from app.db.session import get_sessionmaker
from app.services.campaigns.stages import STAGES, compute_progress, progress_for_stage
from tests.conftest import attach_sample_image, auth_header


async def _ready_to_generate(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await attach_sample_image(client, campaign_id, headers)
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "شال نخی"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    return campaign_id


async def test_repeated_taps_launch_one_job(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_to_generate(client, headers)

    for _ in range(3):
        response = await client.post(
            f"/api/campaigns/{campaign_id}/generate", headers=headers
        )
        assert response.status_code == 200

    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "campaign_generation",
            )
        )
    assert count == 1


async def test_generation_needs_a_brief(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)

    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]

    response = await client.post(
        f"/api/campaigns/{campaign_id}/generate", headers=headers
    )
    assert response.status_code == 422


async def test_polling_after_completion_does_not_duplicate_assets(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_to_generate(client, headers)

    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    for _ in range(4):
        status = await client.get(
            f"/api/campaigns/{campaign_id}/status", headers=headers
        )
        assert status.status_code == 200

    async with get_sessionmaker()() as session:
        types = (
            await session.scalars(
                select(CampaignAsset.asset_type).where(
                    CampaignAsset.campaign_id == uuid.UUID(campaign_id)
                )
            )
        ).all()
    counts = Counter(types)
    assert counts["feed_final"] == 1
    assert counts["story_final"] == 1
    assert sum(counts[kind] for kind in VISUAL_FINAL_TYPES) == 5


def test_progress_walks_every_stage_in_order() -> None:
    total = 10_000
    seen: list[str] = []
    for step in range(0, total, 100):
        progress = compute_progress(step, total)
        if not seen or seen[-1] != progress.stage:
            seen.append(progress.stage)

    assert seen == ["planning", "visual", "finalizing"]
    assert seen == [stage.stage for stage in STAGES]


def test_live_stage_percents_match_the_checklist() -> None:
    planning = progress_for_stage("planning")
    visual = progress_for_stage("visual")
    finalizing = progress_for_stage("finalizing")
    assert planning is not None and planning.percent == 20
    assert visual is not None and visual.percent == 55
    assert finalizing is not None and finalizing.percent == 90
    assert progress_for_stage("captions") is None


def test_progress_never_claims_completion_early() -> None:
    for step in range(0, 9_999, 250):
        assert compute_progress(step, 10_000).percent <= 99


def test_progress_completes_when_time_runs_out() -> None:
    done = compute_progress(10_000, 10_000)
    assert done.done is True
    assert done.percent == 100


@pytest.mark.parametrize("total", [0, -1])
def test_zero_duration_completes_immediately(total: int) -> None:
    """Setting GENERATION_SIMULATED_MS to 0 must not divide by zero."""
    assert compute_progress(0, total).done is True


def test_default_duration_matches_phase_one() -> None:
    """
    Read off the field default, not an instance: the test environment overrides
    this to 0 so the suite does not wait fifteen seconds per campaign.
    """
    from app.core.config import Settings

    total = Settings.model_fields["generation_simulated_ms"].default
    queue = Settings.model_fields["generation_queue_ms"].default
    assert total + queue == 15_600
