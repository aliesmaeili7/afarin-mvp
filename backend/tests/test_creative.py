"""Creative-mode planner, candidates, cost caps, and winner Story."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import CampaignVisualAttempt, CampaignVisualCandidate
from app.db.session import get_sessionmaker
from app.providers.image import set_image_provider
from app.providers.vision import set_visual_planner
from app.providers.vision.base import CandidateQuality, QualityReport
from app.providers.vision.stub import StubVisualPlanner
from tests.conftest import auth_header, png_bytes
from tests.fakes import FakeImageProvider
from tests.test_visuals import _generate, _ready_campaign


async def _creative_campaign(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    uploaded = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        headers=headers,
        files=[("files", ("product.png", png_bytes(512, 640), "image/png"))],
    )
    assert uploaded.status_code == 200
    image_id = uploaded.json()[0]["id"]
    cropped = await client.patch(
        f"/api/campaigns/{campaign_id}/images/{image_id}/crop",
        headers=headers,
        json={"x": 0, "y": 0, "width": 1, "height": 1},
    )
    assert cropped.status_code == 200
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "هودی سرمه‌ای"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={
            "objective": "promotion",
            "visual_style": "friendly",
            "visual_creation_mode": "creative",
        },
    )
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concepts.json()[1]['id']}/select",
        headers=headers,
    )
    saved = await client.post(
        f"/api/campaigns/{campaign_id}/visual/recipe",
        headers=headers,
        json={
            "style_id": "photoreal_commercial",
            "template_id": "hero_product",
            "source": "custom",
        },
    )
    assert saved.status_code == 200
    return campaign_id


async def test_catalog_has_no_prompt_atoms(client: AsyncClient) -> None:
    response = await client.get("/api/visual-catalog")
    assert response.status_code == 200
    body = response.json()
    assert len(body["styles"]) == 14
    assert len(body["templates"]) == 12
    for item in body["styles"] + body["templates"]:
        assert "prompt_atoms" not in item
        assert item["label_fa"]
        assert item["preview_path"].startswith("/visual-previews/")


async def test_accurate_path_still_two_empty_scenes(
    client: AsyncClient, storage
) -> None:
    fake = FakeImageProvider()
    set_image_provider(fake)
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert len(fake.calls) == 2
    assert all(not call.references for call in fake.calls)


async def test_creative_three_candidates_then_story(
    client: AsyncClient, storage
) -> None:
    fake = FakeImageProvider()
    set_image_provider(fake)
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    assert status.json()["status"] == "candidates_ready"

    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    visible = [row for row in detail["visual_candidates"] if not row["hidden"]]
    assert len(visible) == 3
    assert fake.calls[0].n == 3
    assert fake.calls[0].references
    assert all(call.aspect_ratio != "9:16" for call in fake.calls)

    chosen = visible[0]["id"]
    selected = await client.post(
        f"/api/campaigns/{campaign_id}/visual/candidates/{chosen}/select",
        headers=headers,
    )
    assert selected.status_code == 200
    assert selected.json()["status"] == "ready"
    assert any(call.aspect_ratio == "9:16" for call in fake.calls)

    ready = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    feed = next(a for a in ready["assets"] if a["asset_type"] == "feed_final")
    carousel = next(a for a in ready["assets"] if a["asset_type"] == "carousel_1")
    spec = feed["metadata_json"]
    assert spec["product_source"] == "generated"
    assert spec["product_image_path"] is None
    assert spec["scene_image_path"]
    assert carousel["metadata_json"]["scene_image_path"] == spec["scene_image_path"]


async def test_hard_fail_triggers_one_repair(client: AsyncClient, storage) -> None:
    class FailingPlanner(StubVisualPlanner):
        async def score_candidates(self, reference, candidates, context):
            del reference, context
            rows = []
            for index, _frame in enumerate(candidates):
                rows.append(
                    CandidateQuality(
                        slot=index + 1,
                        hard_failed=index == 0 and len(candidates) == 3,
                        identity_recognizable=index != 0 or len(candidates) != 3,
                        no_random_text_or_logos=True,
                        no_severe_artifacts=True,
                        ad_composition=True,
                    )
                )
            return QualityReport(candidates=tuple(rows))

    fake = FakeImageProvider()
    set_image_provider(fake)
    set_visual_planner(FailingPlanner())
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    ns = [call.n for call in fake.calls]
    assert 3 in ns
    assert 1 in ns
    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    hidden = [row for row in detail["visual_candidates"] if row["hidden"]]
    assert hidden


async def test_campaign_attempt_cap(client: AsyncClient, storage, monkeypatch) -> None:
    monkeypatch.setenv("MAX_CREATIVE_ATTEMPTS_PER_CAMPAIGN", "1")
    get_settings.cache_clear()
    fake = FakeImageProvider()
    set_image_provider(fake)
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    first = await _generate(client, headers, campaign_id)
    assert first.json()["status"] == "candidates_ready"
    second = await client.post(
        f"/api/campaigns/{campaign_id}/visual/regenerate",
        headers=headers,
    )
    assert second.status_code in (409, 422)


async def test_regenerate_keeps_previous_attempt(
    client: AsyncClient, storage
) -> None:
    fake = FakeImageProvider()
    set_image_provider(fake)
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    await _generate(client, headers, campaign_id)
    regen = await client.post(
        f"/api/campaigns/{campaign_id}/visual/regenerate",
        headers=headers,
    )
    assert regen.status_code == 200
    factory = get_sessionmaker()
    async with factory() as session:
        attempts = list(
            await session.scalars(
                select(CampaignVisualAttempt).where(
                    CampaignVisualAttempt.campaign_id == campaign_id
                )
            )
        )
        assert len(attempts) == 2
        candidates = list(
            await session.scalars(
                select(CampaignVisualCandidate).where(
                    CampaignVisualCandidate.attempt_id.in_(
                        [row.id for row in attempts]
                    )
                )
            )
        )
        assert len(candidates) >= 6


async def test_custom_generate_does_not_call_planner_quality(
    client: AsyncClient, storage
) -> None:
    class BoomPlanner(StubVisualPlanner):
        async def check_input_quality(self, image, context):
            raise RuntimeError("planner must not run during generate")

    fake = FakeImageProvider()
    set_image_provider(fake)
    set_visual_planner(BoomPlanner())
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    assert status.json()["status"] == "candidates_ready"


async def test_quality_score_failure_still_shows_candidates(
    client: AsyncClient, storage
) -> None:
    class BoomScore(StubVisualPlanner):
        async def score_candidates(self, reference, candidates, context):
            raise RuntimeError("openrouter 400")

    fake = FakeImageProvider()
    set_image_provider(fake)
    set_visual_planner(BoomScore())
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    assert status.json()["status"] == "candidates_ready"
    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    visible = [row for row in detail["visual_candidates"] if not row["hidden"]]
    assert len(visible) == 3


async def test_creative_partial_failed_can_retry_visuals(
    client: AsyncClient, storage
) -> None:
    from tests.fakes import FAILED

    set_image_provider(FakeImageProvider(FAILED))
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post(
        "/api/session/adopt",
        headers=headers,
        json={"display_name": "علی"},
    )
    campaign_id = await _creative_campaign(client, headers)
    first = await _generate(client, headers, campaign_id)
    assert first.json()["status"] == "partial_failed"

    set_image_provider(FakeImageProvider())
    regen = await client.post(
        f"/api/campaigns/{campaign_id}/visual/regenerate",
        headers=headers,
    )
    assert regen.status_code == 200
    assert regen.json()["status"] == "candidates_ready"

