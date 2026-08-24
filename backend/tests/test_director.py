"""Unified Creative Director flow: one multimodal call, persisted directions."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Campaign, CampaignConcept, GenerationJob
from app.db.session import get_sessionmaker
from app.providers.vision.base import InputQuality, PlannerResult
from app.providers.vision.stub import SMART_DIRECTIONS, StubVisualPlanner
from tests.conftest import attach_sample_image, auth_header


async def _brief(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await attach_sample_image(client, campaign_id, headers)
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "هودی سرمه‌ای"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    return campaign_id


async def test_brief_triggers_one_multimodal_planner_job(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    for row in body:
        assert row["raw_json"]["style_id"]
        assert row["raw_json"]["template_id"]

    async with get_sessionmaker()() as session:
        jobs = list(
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.campaign_id == uuid.UUID(campaign_id)
                )
            )
        )
    types = {job.job_type for job in jobs}
    assert types == {"visual_planner"}
    assert all(job.status == "succeeded" for job in jobs)


async def test_needs_fix_does_not_persist_directions(
    client: AsyncClient, storage
) -> None:
    class BrokenCrop(StubVisualPlanner):
        async def plan_directions(self, image, context, *, original=None):
            del image, context, original
            return PlannerResult(
                product_visual_analysis="screenshot chrome covering the product",
                product_type="unknown",
                visual_identity=(),
                identity_constraints=(),
                unsuitable_style_ids=(),
                unsuitable_template_ids=(),
                input_quality=InputQuality("needs_fix", ("screenshot UI",)),
                directions=SMART_DIRECTIONS,
            )

    from app.providers.vision import set_visual_planner

    set_visual_planner(BrokenCrop())
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 422
    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    assert detail["concepts"] == []
    assert detail["campaign"]["status"] == "brief_complete"
    assert detail["campaign"]["planner_result_json"]["input_quality"]["status"] == (
        "needs_fix"
    )


async def test_select_and_mode_make_no_llm_job(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    concept_id = concepts.json()[0]["id"]
    selected = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concept_id}/select",
        headers=headers,
    )
    assert selected.status_code == 200
    recipe = selected.json()["visual_recipe_json"]
    assert recipe["style_id"] == "photoreal_commercial"
    assert recipe["recommended"]["style_id"] == "photoreal_commercial"
    assert recipe["source"] == "smart"

    mode = await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"visual_creation_mode": "accurate"},
    )
    assert mode.status_code == 200
    assert mode.json()["visual_recipe_json"]["style_id"] == "photoreal_commercial"

    override = await client.post(
        f"/api/campaigns/{campaign_id}/visual/recipe",
        headers=headers,
        json={
            "style_id": "neon",
            "template_id": "cinematic_environment",
            "source": "custom",
        },
    )
    assert override.status_code == 200
    saved = override.json()["visual_recipe_json"]
    assert saved["style_id"] == "neon"
    assert saved["source"] == "custom"
    assert saved["recommended"]["style_id"] == "photoreal_commercial"

    async with get_sessionmaker()() as session:
        jobs = list(
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.campaign_id == uuid.UUID(campaign_id)
                )
            )
        )
    assert {job.job_type for job in jobs} == {"visual_planner"}


async def test_copy_and_image_jobs_coexist_after_start(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concepts.json()[0]['id']}/select",
        headers=headers,
    )
    started = await client.post(
        f"/api/campaigns/{campaign_id}/generate", headers=headers
    )
    assert started.status_code == 200
    async with get_sessionmaker()() as session:
        jobs = list(
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.campaign_id == uuid.UUID(campaign_id),
                    GenerationJob.job_type.in_(
                        ("campaign_generation", "image_generation")
                    ),
                )
            )
        )
    types = {job.job_type for job in jobs}
    assert types == {"campaign_generation", "image_generation"}
    assert all(job.status in ("queued", "processing") for job in jobs)


async def test_legacy_concept_rows_still_read(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    concept = concepts.json()[0]
    async with get_sessionmaker()() as session:
        row = await session.get(CampaignConcept, uuid.UUID(concept["id"]))
        assert row is not None
        row.raw_json = {"background_id": "friendly_peach"}
        campaign = await session.get(Campaign, uuid.UUID(campaign_id))
        assert campaign is not None
        campaign.planner_result_json = {}
        await session.commit()

    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert detail.status_code == 200
    loaded = detail.json()["concepts"][0]
    assert loaded["title_fa"]
    assert loaded["raw_json"].get("style_id") is None


async def test_missing_crop_blocks_director(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "هودی"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 422
