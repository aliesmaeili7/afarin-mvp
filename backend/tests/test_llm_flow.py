"""LLM rewrite path using a fake client; no paid calls."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.db.models import GenerationJob
from app.db.session import get_sessionmaker
from app.providers.llm import get_content_provider, set_content_provider
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from tests.conftest import auth_header, attach_sample_image
from tests.fakes import FakeLlmClient, copy_package


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


async def test_rewrite_updates_copy_and_writes_a_job(
    client: AsyncClient, storage
) -> None:
    set_content_provider(
        _provider(
            {"text_fa": "سفارش بده الان"},
            {"text_fa": "زعفران ممتاز قائنات، انتخاب هوشمندانه‌تر"},
        )
    )
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _brief(client, headers)
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
