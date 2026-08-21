"""Empty scenes, cutouts, image jobs and image-only regenerate."""

import os
import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.db.models import Campaign, CampaignAsset, CampaignCopy, GenerationJob
from app.db.session import get_sessionmaker
from app.providers.image import get_image_provider, set_image_provider
from app.providers.image.base import ImageRequest
from app.providers.image.stub import StubImageProvider
from app.providers.llm import set_content_provider
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from tests.conftest import auth_header, png_bytes
from tests.fakes import (
    FAILED,
    FakeImageProvider,
    FakeLlmClient,
    copy_package,
)


async def _ready_campaign(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/api/campaigns/{campaign_id}/images",
        headers=headers,
        files=[("files", ("product.png", png_bytes(), "image/png"))],
    )
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
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concepts.json()[1]['id']}/select",
        headers=headers,
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
    assert scene_45 and "scene-4x5-" in scene_45 and scene_45.endswith(".jpg")
    assert scene_916 and "scene-9x16-" in scene_916 and scene_916.endswith(".jpg")
    assert scene_45 != scene_916
    for key in ("carousel_1", "carousel_2", "carousel_3"):
        assert assets[key]["storage_path"] is None
        assert assets[key]["metadata_json"]["scene_image_path"] == scene_45
    assert "cutouts/" in feed["metadata_json"]["product_image_path"]
    assert feed["metadata_json"]["product_source"] == "cutout"

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
        backgrounds = (
            await session.scalars(
                select(CampaignAsset).where(
                    CampaignAsset.campaign_id == uuid.UUID(campaign_id),
                    CampaignAsset.asset_type == "generated_background",
                )
            )
        ).all()
    assert copy_job is not None and copy_job.status == "succeeded"
    assert image_job is not None and image_job.status == "succeeded"
    assert image_job.provider == "stub"
    assert len(backgrounds) == 2
    sizes = {(row.width, row.height) for row in backgrounds}
    assert sizes == {(1080, 1350), (1080, 1920)}


async def test_image_failure_keeps_copy_and_marks_partial_failed(
    client: AsyncClient, storage
) -> None:
    set_image_provider(FakeImageProvider(FAILED))
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "partial_failed"
    assert "feed_final" in status.json()["failed_asset_types"]
    assert "story_final" in status.json()["failed_asset_types"]

    async with get_sessionmaker()() as session:
        copy_count = await session.scalar(
            select(func.count(CampaignCopy.id)).where(
                CampaignCopy.campaign_id == uuid.UUID(campaign_id)
            )
        )
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
        feed = await session.scalar(
            select(CampaignAsset).where(
                CampaignAsset.campaign_id == uuid.UUID(campaign_id),
                CampaignAsset.asset_type == "feed_final",
            )
        )
    assert copy_count == 9
    assert campaign is not None and campaign.status == "partial_failed"
    assert copy_job is not None and copy_job.status == "succeeded"
    assert image_job is not None and image_job.status == "failed"
    assert feed is not None
    assert feed.metadata_json.get("failed") is True
    assert not feed.metadata_json.get("scene_image_path")


async def test_regenerate_feed_is_image_only_and_updates_carousel(
    client: AsyncClient, storage
) -> None:
    llm = FakeLlmClient([copy_package()])
    set_content_provider(
        OpenRouterContentProvider(
            llm,
            Settings(content_provider="openrouter", openrouter_api_key="sk-test"),
        )
    )
    images = FakeImageProvider()
    set_image_provider(images)

    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "ready"

    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    feed = next(
        row for row in detail.json()["assets"] if row["asset_type"] == "feed_final"
    )
    story = next(
        row for row in detail.json()["assets"] if row["asset_type"] == "story_final"
    )
    before_feed = feed["metadata_json"]["scene_image_path"]
    before_story = story["metadata_json"]["scene_image_path"]
    llm_calls_after_copy = len(llm.calls)

    regenerated = await client.post(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}/regenerate",
        headers=headers,
    )
    assert regenerated.status_code == 200
    assert len(llm.calls) == llm_calls_after_copy
    feed_calls = [call for call in images.calls if call.aspect_ratio == "4:5"]
    story_calls = [call for call in images.calls if call.aspect_ratio == "9:16"]
    assert len(feed_calls) == 2
    assert len(story_calls) == 1
    assert "variation" in feed_calls[-1].prompt
    assert all(call.resolution != "1K" for call in images.calls)
    assert all(call.seed is None for call in images.calls)

    after = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assets = {
        row["asset_type"]: row
        for row in after.json()["assets"]
        if row["asset_type"] != "generated_background"
    }
    current_feed = assets["feed_final"]["metadata_json"]["scene_image_path"]
    assert current_feed != before_feed
    assert assets["carousel_1"]["metadata_json"]["scene_image_path"] == current_feed
    assert assets["carousel_2"]["metadata_json"]["scene_image_path"] == current_feed
    assert assets["story_final"]["metadata_json"]["scene_image_path"] == before_story

    reload = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    reloaded_feed = next(
        row for row in reload.json()["assets"] if row["asset_type"] == "feed_final"
    )
    assert reloaded_feed["metadata_json"]["scene_image_path"] == current_feed

    from app.services.storage.paths import parse

    before_ref = parse(before_feed)
    after_ref = parse(current_feed)
    assert before_ref is not None and after_ref is not None
    before_bytes = storage.objects[f"{before_ref.bucket}/{before_ref.key}"]
    after_bytes = storage.objects[f"{after_ref.bucket}/{after_ref.key}"]
    assert before_bytes != after_bytes
    assert (
        assets["feed_final"]["metadata_json"]["headline_fa"]
        == feed["metadata_json"]["headline_fa"]
    )
