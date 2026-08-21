"""LLM-backed campaign flow using a fake client; no paid calls."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.db.models import Campaign, CampaignCopy, GenerationJob
from app.db.session import get_sessionmaker
from app.providers.llm import get_content_provider, set_content_provider
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from app.providers.vision import set_visual_planner
from app.providers.vision.openrouter import OpenRouterVisualPlanner
from tests.conftest import auth_header, attach_sample_image
from tests.fakes import FAILED, FakeLlmClient, copy_package, three_directions


def _provider(*payloads: dict | Exception) -> OpenRouterContentProvider:
    settings = Settings(
        content_provider="openrouter",
        openrouter_api_key="sk-test",
        llm_model="openai/gpt-5-mini",
        llm_max_retries=0,
    )
    return OpenRouterContentProvider(FakeLlmClient(list(payloads)), settings)


async def _brief(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await attach_sample_image(client, campaign_id, headers)
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "زعفران ممتاز قائنات", "brand_name": "آرین"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "sell_product", "visual_style": "luxury"},
    )
    return campaign_id


def _planner(*payloads: dict | Exception) -> OpenRouterVisualPlanner:
    settings = Settings(
        content_provider="openrouter",
        openrouter_api_key="sk-test",
        visual_planner_model="openai/gpt-5-mini",
        llm_max_retries=0,
    )
    return OpenRouterVisualPlanner(FakeLlmClient(list(payloads)), settings)


def _user_text(call: dict) -> str:
    content = call["messages"][1]["content"]
    if isinstance(content, list):
        return next(part["text"] for part in content if part.get("type") == "text")
    return str(content)


async def test_concepts_persist_three_rows(client: AsyncClient, storage) -> None:
    set_visual_planner(_planner(three_directions()))
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["raw_json"]["style_id"] == "photoreal_commercial"
    assert body[0]["raw_json"]["template_id"] == "hero_product"
    assert body[0]["raw_json"]["background_id"] in ("luxury_night", "luxury_velvet")
    assert {row["raw_json"]["style_id"] for row in body} == {
        "photoreal_commercial",
        "anime",
        "surreal",
    }

    async with get_sessionmaker()() as session:
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "visual_planner",
            )
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.provider == "openrouter"
        assert job.model == "openai/gpt-5-mini"
        assert job.prompt_tokens == 11


async def test_materialize_writes_nine_copy_rows(client: AsyncClient, storage) -> None:
    set_content_provider(_provider(copy_package()))
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
    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    status = await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)
    assert status.json()["status"] == "ready"

    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count(CampaignCopy.id)).where(
                CampaignCopy.campaign_id == uuid.UUID(campaign_id)
            )
        )
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "campaign_generation",
            )
        )
    assert count == 9
    assert job is not None
    assert job.status == "succeeded"
    assert job.provider == "openrouter"


async def test_failed_llm_marks_campaign_failed(client: AsyncClient, storage) -> None:
    set_visual_planner(
        OpenRouterVisualPlanner(
            FakeLlmClient(FAILED),
            Settings(content_provider="openrouter", openrouter_api_key="sk-test"),
        )
    )
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 500
    assert response.json()["code"] == "generation_failed"
    assert "دوباره امتحان کن" in response.json()["message_fa"]

    async with get_sessionmaker()() as session:
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id)
            )
        )
    assert job is not None
    assert job.status == "failed"


async def test_failed_copy_marks_campaign_failed(client: AsyncClient, storage) -> None:
    set_content_provider(_provider(FAILED))
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
    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    status = await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert "دوباره امتحان کن" in (status.json()["message_fa"] or "")

    async with get_sessionmaker()() as session:
        campaign = await session.get(Campaign, uuid.UUID(campaign_id))
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "campaign_generation",
            )
        )
    assert campaign is not None
    assert campaign.status == "failed"
    assert job is not None
    assert job.status == "failed"


async def test_rewrite_updates_copy_and_writes_a_job(
    client: AsyncClient, storage
) -> None:
    set_content_provider(
        _provider(
            copy_package(),
            {"text_fa": "سفارش بده الان"},
            {"text_fa": "زعفران ممتاز قائنات، انتخاب هوشمندانه‌تر"},
        )
    )
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
    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)

    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    cta = next(item for item in detail["copies"] if item["copy_type"] == "cta")
    rewritten = await client.post(
        f"/api/campaigns/{campaign_id}/copy/{cta['id']}/rewrite",
        headers=headers,
        json={"intent": "stronger_cta"},
    )
    assert rewritten.status_code == 200
    assert rewritten.json()["content"] == "سفارش بده الان"

    feed = next(item for item in detail["assets"] if item["asset_type"] == "feed_final")
    headline = await client.post(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}/rewrite",
        headers=headers,
        json={"intent": "new_headline"},
    )
    assert headline.status_code == 200
    assert "انتخاب هوشمندانه‌تر" in headline.json()["metadata_json"]["headline_fa"]

    async with get_sessionmaker()() as session:
        jobs = (
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.campaign_id == uuid.UUID(campaign_id),
                    GenerationJob.job_type == "copy_rewrite",
                )
            )
        ).all()
    assert len(jobs) == 2
    assert all(job.status == "succeeded" for job in jobs)


async def test_openrouter_without_key_does_not_stub(monkeypatch) -> None:
    set_content_provider(None)
    monkeypatch.setenv("CONTENT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(ApiError) as caught:
            get_content_provider()
        assert caught.value.code == "generation_failed"
    finally:
        monkeypatch.setenv("CONTENT_PROVIDER", "stub")
        get_settings.cache_clear()


async def test_regenerating_concepts_sends_previous_ideas(
    client: AsyncClient, storage
) -> None:
    fake = FakeLlmClient([three_directions(), three_directions()])
    set_visual_planner(
        OpenRouterVisualPlanner(
            fake,
            Settings(
                content_provider="openrouter",
                openrouter_api_key="sk-test",
                visual_planner_model="openai/gpt-5-mini",
                llm_max_retries=0,
            ),
        )
    )
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)

    first = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert first.status_code == 200
    again = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert again.status_code == 200

    first_prompt = _user_text(fake.calls[0])
    second_prompt = _user_text(fake.calls[1])
    assert "واقعی و واضح" not in first_prompt
    assert "واقعی و واضح" in second_prompt
    assert "photoreal_commercial" in second_prompt
    assert "Do not paraphrase" in second_prompt
