"""Empty scenes, cutouts, image jobs and image-only regenerate."""

import os
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import Campaign, GenerationJob
from app.db.session import get_sessionmaker
from app.providers.image import get_image_provider, set_image_provider
from app.providers.image.base import ImageRequest
from app.providers.image.stub import StubImageProvider
from tests.conftest import attach_sample_image, auth_header
from tests.fakes import (
    FAILED,
    FakeImageProvider,
)


async def _ready_campaign(client: AsyncClient, headers: dict[str, str]) -> str:
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


async def _generate(client: AsyncClient, headers: dict[str, str], campaign_id: str):
    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    return await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)


async def test_stub_provider_returns_a_jpeg() -> None:
    result = await StubImageProvider().generate(
        ImageRequest(prompt="empty studio, no text", aspect_ratio="4:5")
    )
    assert result.media_type == "image/jpeg"
    assert result.content[:2] == b"\xff\xd8"


def test_openrouter_without_a_key_does_not_stub() -> None:
    set_image_provider(None)
    os.environ["IMAGE_PROVIDER"] = "openrouter"
    os.environ["OPENROUTER_API_KEY"] = ""
    get_settings.cache_clear()
    try:
        raised: ApiError | None = None
        try:
            get_image_provider()
        except ApiError as error:
            raised = error
        assert raised is not None
        assert raised.code == "generation_failed"
    finally:
        os.environ["IMAGE_PROVIDER"] = "stub"
        get_settings.cache_clear()
        set_image_provider(None)


async def test_materialize_wires_shared_scenes_and_keeps_finals_pathless(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "ready"

    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assets = {
        row["asset_type"]: row
        for row in detail.json()["assets"]
        if row["asset_type"] != "generated_background"
    }
    feed = assets["feed_final"]
    story = assets["story_final"]

    assert feed["storage_path"] is None
    assert story["storage_path"] is None
    scene_45 = feed["metadata_json"]["scene_image_path"]
    scene_916 = story["metadata_json"]["scene_image_path"]
    assert scene_45
    assert scene_916 == scene_45
    for key in ("carousel_1", "carousel_2", "carousel_3"):
        assert assets[key]["storage_path"] is None
        assert assets[key]["metadata_json"]["scene_image_path"] == scene_45
    assert feed["metadata_json"].get("product_image_path") in (None, "")
    assert feed["metadata_json"]["product_source"] == "generated"

    async with get_sessionmaker()() as session:
        image_job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "image_generation",
            )
        )
        copy_job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "campaign_generation",
            )
        )
    assert copy_job is not None and copy_job.status == "succeeded"
    assert image_job is not None and image_job.status == "succeeded"
    assert image_job.provider == "stub"


async def test_image_failure_marks_partial_failed(
    client: AsyncClient, storage
) -> None:
    set_image_provider(FakeImageProvider(FAILED))
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "partial_failed"

    async with get_sessionmaker()() as session:
        campaign = await session.get(Campaign, uuid.UUID(campaign_id))
        image_job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "image_generation",
            )
        )
        copy_job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "campaign_generation",
            )
        )
    assert campaign is not None and campaign.status == "partial_failed"
    assert copy_job is not None and copy_job.status == "succeeded"
    assert image_job is not None and image_job.status == "failed"

