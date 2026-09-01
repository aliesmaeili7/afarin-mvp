"""Unified Creative Agent production path. Stub providers only."""

from __future__ import annotations

from dataclasses import replace

from httpx import AsyncClient

import uuid

from app.content.visual_catalog import public_catalog, template_ids
from app.providers.image import set_image_provider
from app.providers.vision.base import CreativeAgentContext
from app.providers.vision.creative_validate import validate_creative_result
from app.providers.vision.stub import StubCreativeAgent, stub_creative_result
from app.services.campaigns.creative_core import generate_recipe_set
from tests.conftest import auth_header, png_bytes
from tests.fakes import FakeImageProvider
from tests.test_visuals import _generate


def _context(**overrides) -> CreativeAgentContext:
    base = CreativeAgentContext(
        product_name="هودی سرمه‌ای",
        description="هودی نخی",
        brand_name=None,
        price_text=None,
        audience="جوانان",
        objective="sell_product",
        visual_style="modern",
        requested_image_count=1,
    )
    return replace(base, **overrides)


async def _briefed_campaign(client: AsyncClient, headers: dict[str, str]) -> str:
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
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    return campaign_id


def test_unified_catalog_is_templates_only() -> None:
    body = public_catalog()
    assert "styles" not in body
    assert len(body["templates"]) == len(template_ids()) == 26
    for item in body["templates"]:
        assert "creative_guidance" not in item
        assert "prompt_guidance" not in item
        assert item["label_fa"]
        assert item["preview_path"].startswith("/visual-previews/")


def test_stub_agent_count_one_and_three() -> None:
    one = stub_creative_result(_context(requested_image_count=1), image=b"jpeg")
    three = stub_creative_result(_context(requested_image_count=3), image=b"jpeg")
    assert len(one.images) == 1
    assert len(three.images) == 3
    assert validate_creative_result(one, requested_image_count=1).ok
    assert validate_creative_result(three, requested_image_count=3).ok
    prompts = [item.final_prompt for item in three.images]
    assert len(set(prompts)) == 3


def test_optional_template_and_instruction_priority() -> None:
    templated = stub_creative_result(
        _context(template_id="product_pedestal"), image=b"jpeg"
    )
    instructed = stub_creative_result(
        _context(
            template_id="product_pedestal",
            visual_instruction="dark marble plinth, low camera",
        ),
        image=b"jpeg",
    )
    free = stub_creative_result(_context(), image=b"jpeg")
    assert templated.images[0].visual_plan.template_id == "product_pedestal"
    assert free.images[0].visual_plan.template_id is None
    assert "dark marble plinth" in instructed.images[0].final_prompt
    assert "seller direction" in instructed.images[0].final_prompt.lower() or (
        "dark marble" in instructed.images[0].final_prompt
    )


def test_persian_copy_is_on_each_concept() -> None:
    result = stub_creative_result(_context(requested_image_count=3), image=b"jpeg")
    for item in result.images:
        copy = item.copy
        assert copy.on_image_headline
        assert copy.feed_caption
        assert copy.story_text
        assert copy.cta
        assert copy.hashtags


def test_malformed_result_fails_validation() -> None:
    result = stub_creative_result(_context(requested_image_count=1), image=b"jpeg")
    bad = replace(result, images=())
    check = validate_creative_result(bad, requested_image_count=1)
    assert not check.ok


async def test_seedream_receives_final_prompt_and_reference() -> None:
    fake = FakeImageProvider()
    set_image_provider(fake)
    out = await generate_recipe_set(
        context=_context(requested_image_count=1),
        reference=png_bytes(512, 640),
        provider=fake,
        agent=StubCreativeAgent(),
        quality_check=False,
        repair="none",
    )
    assert out.error is None
    assert len(out.candidates) == 1
    assert len(fake.calls) == 1
    expected = stub_creative_result(_context(), image=b"x").images[0].final_prompt
    assert fake.calls[0].prompt == expected
    assert fake.calls[0].references
    assert len(fake.calls[0].prompt) <= 800
    assert not fake.calls[0].prompt.strip().startswith("{")


async def test_three_images_are_requested_in_parallel() -> None:
    fake = FakeImageProvider()
    out = await generate_recipe_set(
        context=_context(requested_image_count=3),
        reference=png_bytes(512, 640),
        provider=fake,
        agent=StubCreativeAgent(),
        quality_check=False,
        repair="none",
    )
    assert out.error is None
    assert len(out.candidates) == 3
    assert len(fake.calls) == 3
    prompts = [call.prompt for call in fake.calls]
    assert len(set(prompts)) == 3
    assert out.requested_image_count == 3


async def test_invalid_agent_output_makes_zero_seedream_calls() -> None:
    class BadAgent(StubCreativeAgent):
        async def create_campaign(self, image, context, *, correction=None):
            result = await super().create_campaign(
                image, context, correction=correction
            )
            return replace(result, images=())

    fake = FakeImageProvider()
    out = await generate_recipe_set(
        context=_context(requested_image_count=1),
        reference=png_bytes(512, 640),
        provider=fake,
        agent=BadAgent(),
        quality_check=False,
        repair="none",
    )
    assert out.error
    assert fake.calls == []
    assert out.candidates == []


async def test_one_retry_then_valid(monkeypatch) -> None:
    calls = {"n": 0}

    class Flaky(StubCreativeAgent):
        async def create_campaign(self, image, context, *, correction=None):
            calls["n"] += 1
            result = await super().create_campaign(
                image, context, correction=correction
            )
            if calls["n"] == 1:
                return replace(result, images=())
            return result

    fake = FakeImageProvider()
    out = await generate_recipe_set(
        context=_context(requested_image_count=1),
        reference=png_bytes(512, 640),
        provider=fake,
        agent=Flaky(),
        quality_check=False,
        repair="none",
    )
    assert calls["n"] == 2
    assert out.error is None
    assert len(fake.calls) == 1


async def test_production_generate_one_image(client: AsyncClient, storage) -> None:
    fake = FakeImageProvider()
    set_image_provider(fake)
    headers = auth_header(uuid.uuid4())
    await client.post(
        "/api/session/adopt", headers=headers, json={"display_name": "علی"}
    )
    campaign_id = await _briefed_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert len(fake.calls) == 1
    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    body = detail.json()
    visible = [row for row in body["visual_candidates"] if not row["hidden"]]
    assert len(visible) == 1
    copies = body["copies"]
    assert any(row["copy_type"] == "caption_persuasive" for row in copies)
    assert any(row["copy_type"] == "story" for row in copies)
    feed = next(asset for asset in body["assets"] if asset["asset_type"] == "feed_final")
    assert feed["metadata_json"]["headline_fa"]
    assert feed["metadata_json"]["scene_image_path"]
    assert feed["metadata_json"].get("product_image_path") in (None, "")


async def test_removed_routes_are_gone(client: AsyncClient) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post(
        "/api/session/adopt", headers=headers, json={"display_name": "علی"}
    )
    campaign_id = await _briefed_campaign(client, headers)
    missing = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    assert missing.status_code == 404
    recipe = await client.post(
        f"/api/campaigns/{campaign_id}/visual/recipe",
        headers=headers,
        json={"style_id": "x", "template_id": "y"},
    )
    assert recipe.status_code == 404


def test_old_services_are_not_importable() -> None:
    import importlib

    for module in (
        "app.services.campaigns.planner",
        "app.services.campaigns.render_strategy",
        "app.services.campaigns.product_composite",
        "app.providers.vision.architect_validate",
    ):
        try:
            importlib.import_module(module)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"{module} should be removed")
