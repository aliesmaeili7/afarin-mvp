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
from tests.conftest import auth_header
from tests.fakes import FAILED, FakeLlmClient, copy_package, three_concepts


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


async def test_concepts_persist_three_rows(client: AsyncClient, storage) -> None:
    set_content_provider(_provider(three_concepts()))
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert "زعفران ممتاز قائنات" in body[0]["headline_fa"]
    assert body[0]["raw_json"]["background_id"] in ("luxury_night", "luxury_velvet")

    async with get_sessionmaker()() as session:
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == uuid.UUID(campaign_id),
                GenerationJob.job_type == "concept_generation",
            )
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.provider == "openrouter"
        assert job.model == "openai/gpt-5-mini"
        assert job.prompt_tokens == 11


async def test_materialize_writes_nine_copy_rows(client: AsyncClient, storage) -> None:
    set_content_provider(_provider(three_concepts(), copy_package()))
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
    set_content_provider(
        OpenRouterContentProvider(
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
    set_content_provider(_provider(three_concepts(), FAILED))
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
            three_concepts(),
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
    fake = FakeLlmClient([three_concepts(), three_concepts()])
    set_content_provider(
        OpenRouterContentProvider(
            fake,
            Settings(
                content_provider="openrouter",
                openrouter_api_key="sk-test",
                llm_model="openai/gpt-5-mini",
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

    first_prompt = fake.calls[0]["messages"][1]["content"]
    second_prompt = fake.calls[1]["messages"][1]["content"]
    assert "هدیه شبانه" not in first_prompt
    assert "هدیه شبانه" in second_prompt
    assert "پس‌زمینه تیره و نور طلایی" in second_prompt
    assert "بازنویسی" in second_prompt
    assert "تخفیف" in fake.calls[0]["messages"][0]["content"]
    assert "واتساپ" in fake.calls[0]["messages"][0]["content"]
