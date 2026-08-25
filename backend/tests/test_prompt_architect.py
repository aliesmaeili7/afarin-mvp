"""Prompt Architect v1: prep, compiler, crop invalidation, Seedream refs."""

from __future__ import annotations

import io
import uuid

from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

from app.content.visual_catalog import DISCOURAGED_WARNING_FA, compatibility
from app.db.models import Campaign, GenerationJob, ProductImage
from app.db.session import get_sessionmaker
from app.providers.image import set_image_provider
from app.providers.image.creative_prompts import (
    INVENTED_TEXT_RULE,
)
from app.providers.vision.architect_validate import (
    FINAL_PROMPT_MAX_CHARS,
    validate_architect_result,
)
from app.providers.vision.stub import SMART_DIRECTIONS, stub_architect_result
from app.services.campaigns.crop import (
    CropRect,
    crop_iou,
    is_material_crop_change,
    should_offer_tighter_crop,
)
from app.services.campaigns.cutout import PassthroughCutout, set_cutout
from app.services.campaigns.recipes import recipe_from_ids
from app.services.campaigns.reference_prep import decide_strategy, prepare_clean_jpeg
from tests.conftest import auth_header
from tests.fakes import FakeImageProvider
from tests.test_creative import _creative_campaign
from tests.test_visuals import _generate


def _jpeg(width: int = 320, height: int = 400, color=(40, 80, 120)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG")
    return buffer.getvalue()


class PunchCutout:
    """Opaque center, transparent border — passes subject-fraction checks."""

    async def remove_background(self, image_bytes: bytes) -> bytes | None:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = image.size
        margin = max(8, min(width, height) // 6)
        pixels = image.load()
        assert pixels is not None
        for y in range(height):
            for x in range(width):
                if (
                    x < margin
                    or y < margin
                    or x >= width - margin
                    or y >= height - margin
                ):
                    red, green, blue, _alpha = pixels[x, y]
                    pixels[x, y] = (red, green, blue, 0)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


def test_crop_iou_material_vs_peripheral_trim() -> None:
    full = CropRect(0.0, 0.0, 1.0, 1.0)
    trim = CropRect(0.02, 0.02, 0.96, 0.96)
    tight = CropRect(0.2, 0.2, 0.5, 0.5)
    assert crop_iou(full, trim) >= 0.85
    assert not is_material_crop_change(full, trim)
    assert is_material_crop_change(full, tight)
    assert should_offer_tighter_crop(full, tight)


def test_compatibility_examples() -> None:
    assert compatibility("fashion_editorial", "hero_product") == "discouraged"
    assert compatibility("cinematic", "hero_product") == "discouraged"
    assert compatibility("photoreal_commercial", "illustrated_scene") == "discouraged"
    assert compatibility("render_3d", "model_using") == "discouraged"
    assert compatibility("clay", "model_using") == "discouraged"
    assert compatibility("fashion_editorial", "model_using") == "preferred"
    assert compatibility("photoreal_commercial", "hero_product") == "preferred"


def test_custom_discouraged_recipe_warns() -> None:
    recipe = recipe_from_ids("fashion_editorial", "hero_product", source="custom")
    assert recipe["compatibility"] == "discouraged"
    assert recipe["warning_fa"] == DISCOURAGED_WARNING_FA


def test_stub_director_is_not_forced_surreal() -> None:
    ids = {(item.style_id, item.template_id) for item in SMART_DIRECTIONS}
    assert ("photoreal_commercial", "hero_product") in ids
    assert ("photoreal_commercial", "model_using") in ids
    assert ("surreal", "giant_miniature_world") not in ids


def test_stub_slots_differ_structurally() -> None:
    planned = stub_architect_result()
    assert len(planned.candidates) == 3
    cameras = {item.composition.camera for item in planned.candidates}
    environments = {item.scene.environment for item in planned.candidates}
    safe = {item.typography_safe_area.position for item in planned.candidates}
    prompts = {item.final_prompt for item in planned.candidates}
    assert len(cameras) == 3
    assert len(environments) == 3
    assert len(safe) == 3
    assert len(prompts) == 3
    assert all(item.final_prompt for item in planned.candidates)
    assert all(
        len(item.final_prompt) <= FINAL_PROMPT_MAX_CHARS for item in planned.candidates
    )
    validation = validate_architect_result(
        planned, render_strategy="reference_transform"
    )
    assert validation.ok


def test_validator_pass_through_does_not_rewrite() -> None:
    planned = stub_architect_result()
    original = planned.candidates[0].final_prompt
    validation = validate_architect_result(
        planned, render_strategy="reference_transform"
    )
    assert validation.ok
    assert planned.candidates[0].final_prompt is original
    assert planned.candidates[0].final_prompt == original


def test_validator_rejects_bad_aspect_missing_safe_area_and_oversize() -> None:
    from dataclasses import replace

    planned = stub_architect_result()
    bad_aspect = replace(
        planned.candidates[0],
        output=replace(planned.candidates[0].output, aspect_ratio="1:1"),
    )
    missing_safe = replace(
        planned.candidates[1],
        typography_safe_area=replace(
            planned.candidates[1].typography_safe_area, position="", description=""
        ),
    )
    oversize = replace(
        planned.candidates[2],
        final_prompt=("this exact product on a table. " * 80)[:900],
    )
    result = replace(planned, candidates=(bad_aspect, missing_safe, oversize))
    validation = validate_architect_result(
        result, render_strategy="reference_transform"
    )
    assert not validation.ok
    blob = " ".join(validation.errors)
    assert "4:5" in blob
    assert "typography_safe_area" in blob
    assert "exceeds 800" in blob


def test_validator_rejects_strategy_mismatch_and_section_dump() -> None:
    from dataclasses import replace

    planned = stub_architect_result()
    dumped = replace(
        planned.candidates[0],
        final_prompt="VISUAL EXECUTION\nthis exact product on a table with empty type space.",
        render_strategy="preserved_product_composite",
    )
    result = replace(
        planned, candidates=(dumped, planned.candidates[1], planned.candidates[2])
    )
    validation = validate_architect_result(
        result, render_strategy="reference_transform"
    )
    assert not validation.ok
    blob = " ".join(validation.errors)
    assert "render_strategy" in blob
    assert "section dump" in blob


def test_seedream_prompt_equals_final_prompt() -> None:
    from types import SimpleNamespace

    from app.providers.vision.base import PlannerContext
    from app.services.campaigns.creative_core import generate_recipe_set
    from app.services.campaigns.recipes import recipe_from_ids
    from tests.fakes import FakeImageProvider

    async def run() -> None:
        fake = FakeImageProvider()
        result = await generate_recipe_set(
            recipe=recipe_from_ids(
                "fashion_editorial", "model_using", source="eval_fixed"
            ),
            reference=_jpeg(),
            campaign=SimpleNamespace(visual_style="friendly"),
            concept=None,
            planner_context=PlannerContext(
                product_name="هودی",
                description=None,
                brand_name=None,
                price_text=None,
                audience=None,
                objective="sell_product",
                visual_style="friendly",
            ),
            provider=fake,
            planner=None,
            n=1,
        )
        assert result.error is None
        assert result.architect is not None
        final = result.architect["candidates"][0]["final_prompt"]
        assert fake.calls[0].prompt == final
        assert result.prompt == final
        assert "VISUAL EXECUTION" not in final
        assert "DO NOT ADD" not in final
        assert INVENTED_TEXT_RULE in final
        assert len(final) <= FINAL_PROMPT_MAX_CHARS
        assert result.architect["validation"]["ok"] is True
        assert result.image_requests[0]["prompt"] == final

    import asyncio

    asyncio.run(run())


def test_passthrough_cutout_is_rejected() -> None:
    async def run() -> None:
        set_cutout(PassthroughCutout())
        result = await prepare_clean_jpeg(
            original=_jpeg(),
            crop_jpeg=_jpeg(),
            analysis={"reference_strategy": "subject_cutout_neutral"},
        )
        assert result.blocked
        assert result.jpeg is None

    import asyncio

    asyncio.run(run())


def test_successful_cutout_is_not_the_original() -> None:
    original = _jpeg(color=(10, 20, 30))

    async def run() -> None:
        set_cutout(PunchCutout())
        result = await prepare_clean_jpeg(
            original=original,
            crop_jpeg=original,
            analysis={"reference_strategy": "subject_cutout_neutral"},
        )
        assert not result.blocked
        assert result.jpeg is not None
        assert result.jpeg != original
        assert result.used_cutout

    import asyncio

    asyncio.run(run())


def test_overlap_strategy_blocks() -> None:
    assert (
        decide_strategy({"cleanliness": "overlapping_contamination"})
        == "needs_user_action"
    )
    assert decide_strategy(
        {"person_present": True, "reference_strategy": "subject_cutout_neutral"}
    ) == ("preserve_context_crop")


async def test_seedream_gets_only_cleaned_reference(
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
    assert all(call.n == 1 for call in fake.calls)
    assert all(len(call.references) == 1 for call in fake.calls)
    ref_bytes = fake.calls[0].references[0]
    async with get_sessionmaker()() as session:
        campaign = await session.get(Campaign, uuid.UUID(campaign_id))
        assert campaign is not None
        image = (
            await session.scalars(
                select(ProductImage).where(
                    ProductImage.product_id == campaign.product_id
                )
            )
        ).first()
        assert image is not None
        assert image.clean_reference_storage_path
        from app.services.storage import parse as parse_ref

        original_ref = parse_ref(image.storage_path)
        clean_ref = parse_ref(image.clean_reference_storage_path)
        assert original_ref is not None and clean_ref is not None
        original = storage.objects[f"{original_ref.bucket}/{original_ref.key}"]
        cleaned = storage.objects[f"{clean_ref.bucket}/{clean_ref.key}"]
        assert ref_bytes == cleaned
        assert ref_bytes != original
        jobs = list(
            await session.scalars(
                select(GenerationJob).where(GenerationJob.campaign_id == campaign.id)
            )
        )
    types = {job.job_type for job in jobs}
    assert "prompt_architect" in types
    assert "visual_quality_check" in types
    assert "image_generation" in types


async def test_small_crop_trim_keeps_director(client: AsyncClient, storage) -> None:
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _creative_campaign(client, headers)
    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    image_id = detail["product_images"][0]["id"]
    concepts = detail["concepts"]
    patched = await client.patch(
        f"/api/campaigns/{campaign_id}/images/{image_id}/crop",
        headers=headers,
        json={"x": 0.01, "y": 0.01, "width": 0.98, "height": 0.98},
    )
    assert patched.status_code == 200
    after = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    assert after["campaign"]["status"] == "concept_selected"
    assert len(after["concepts"]) == len(concepts)
    assert after["campaign"]["planner_result_json"]


async def test_material_crop_invalidates_director(client: AsyncClient, storage) -> None:
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _creative_campaign(client, headers)
    detail = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    image_id = detail["product_images"][0]["id"]
    patched = await client.patch(
        f"/api/campaigns/{campaign_id}/images/{image_id}/crop",
        headers=headers,
        json={"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
    )
    assert patched.status_code == 200
    after = (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    assert after["campaign"]["status"] == "brief_complete"
    assert after["concepts"] == []
    assert after["campaign"]["planner_result_json"] == {}


def _isolatable_analysis(**overrides: object) -> dict:
    payload = {
        "cleanliness": "isolatable_subject",
        "person_present": False,
        "useful_context_present": False,
        "product_visibility": "good",
        "reference_strategy": "direct_crop",
    }
    payload.update(overrides)
    return payload


def test_selector_jar_pedestal_with_cutout_is_preserved() -> None:
    from app.services.campaigns.render_strategy import (
        PRESERVED_PRODUCT_COMPOSITE,
        REFERENCE_TRANSFORM,
        choose_creative_render_strategy,
    )

    png = asyncio_run_cutout()
    choice = choose_creative_render_strategy(
        style_id="photoreal_commercial",
        template_id="product_pedestal",
        analysis=_isolatable_analysis(),
        product_type="cosmetics",
        cutout_png=png,
    )
    assert choice.strategy == PRESERVED_PRODUCT_COMPOSITE

    worn = choose_creative_render_strategy(
        style_id="fashion_editorial",
        template_id="model_using",
        analysis=_isolatable_analysis(),
        product_type="hoodie",
        cutout_png=png,
    )
    assert worn.strategy == REFERENCE_TRANSFORM

    person = choose_creative_render_strategy(
        style_id="photoreal_commercial",
        template_id="hero_product",
        analysis=_isolatable_analysis(person_present=True),
        product_type="cosmetics",
        cutout_png=png,
    )
    assert person.strategy == REFERENCE_TRANSFORM

    none = choose_creative_render_strategy(
        style_id="photoreal_commercial",
        template_id="product_pedestal",
        analysis=_isolatable_analysis(),
        product_type="cosmetics",
        cutout_png=None,
    )
    assert none.strategy == REFERENCE_TRANSFORM


def asyncio_run_cutout() -> bytes:
    import asyncio

    async def run() -> bytes:
        set_cutout(PunchCutout())
        png = await PunchCutout().remove_background(_jpeg(color=(180, 20, 20)))
        assert png is not None
        return png

    return asyncio.run(run())


def test_passthrough_cutout_is_not_preserved() -> None:
    from app.services.campaigns.reference_prep import extract_validated_cutout
    from app.services.campaigns.render_strategy import (
        REFERENCE_TRANSFORM,
        choose_creative_render_strategy,
    )

    async def run() -> None:
        set_cutout(PassthroughCutout())
        png = await extract_validated_cutout(_jpeg())
        assert png is None
        choice = choose_creative_render_strategy(
            style_id="photoreal_commercial",
            template_id="product_pedestal",
            analysis=_isolatable_analysis(),
            product_type="cosmetics",
            cutout_png=png,
        )
        assert choice.strategy == REFERENCE_TRANSFORM

    import asyncio

    asyncio.run(run())


def test_scene_request_has_no_product_reference() -> None:
    from decimal import Decimal
    from types import SimpleNamespace

    from app.providers.image.base import ImageResult, ImageUsage
    from app.providers.vision.base import PlannerContext
    from app.services.campaigns.creative_core import generate_recipe_set
    from app.services.campaigns.recipes import recipe_from_ids
    from tests.fakes import FakeImageProvider

    async def run() -> None:
        set_cutout(PunchCutout())
        fake = FakeImageProvider()
        scene = io.BytesIO()
        Image.new("RGB", (400, 500), (30, 120, 40)).save(scene, format="JPEG")
        fake.results = [
            ImageResult(
                content=scene.getvalue(),
                media_type="image/jpeg",
                usage=ImageUsage(latency_ms=4, cost_usd=Decimal("0"), model="fake"),
            )
        ]
        result = await generate_recipe_set(
            recipe=recipe_from_ids(
                "photoreal_commercial", "product_pedestal", source="eval_fixed"
            ),
            reference=_jpeg(color=(180, 20, 20)),
            campaign=SimpleNamespace(visual_style="luxury"),
            concept=None,
            planner_context=PlannerContext(
                product_name="کرم",
                description=None,
                brand_name=None,
                price_text=None,
                audience=None,
                objective="sell_product",
                visual_style="luxury",
            ),
            provider=fake,
            planner=None,
            n=1,
            analysis=_isolatable_analysis(),
            product_type="cosmetics",
            category="cosmetics",
        )
        assert result.render_strategy == "preserved_product_composite"
        assert fake.calls
        assert fake.calls[0].references == ()
        assert "no product drawn" in result.prompt
        assert result.prompt == result.architect["candidates"][0]["final_prompt"]
        assert "this exact seller product" not in result.prompt

    import asyncio

    asyncio.run(run())


def test_cutout_pixels_survive_paste() -> None:
    from app.providers.vision.base import ProductPlacement
    from app.services.campaigns.product_composite import composite_cutout_onto_scene

    scene = io.BytesIO()
    Image.new("RGB", (400, 500), (10, 180, 20)).save(scene, format="JPEG")
    cut = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
    pixels = cut.load()
    assert pixels is not None
    for y in range(40, 220):
        for x in range(30, 170):
            pixels[x, y] = (220, 30, 30, 255)
    buf = io.BytesIO()
    cut.save(buf, format="PNG")
    composed = composite_cutout_onto_scene(
        scene.getvalue(),
        buf.getvalue(),
        ProductPlacement(x=0.5, y=0.55, width=0.4, contact_surface="plinth"),
    )
    image = Image.open(io.BytesIO(composed)).convert("RGB")
    sample = image.getpixel((200, 275))
    assert sample[0] > sample[1]
    assert sample[0] > 150


def test_unusable_preserved_placement_retries_as_transform() -> None:
    from dataclasses import replace
    from types import SimpleNamespace

    from app.providers.vision.base import PlannerContext, PromptArchitectResult
    from app.providers.vision.stub import StubPromptArchitect
    from app.services.campaigns.creative_core import generate_recipe_set
    from app.services.campaigns.recipes import recipe_from_ids
    from tests.fakes import FakeImageProvider

    class FlipArchitect:
        name = "flip"
        model = None

        def __init__(self) -> None:
            self.calls = 0
            self._inner = StubPromptArchitect()
            self.scene_prompt = ""

        async def plan_candidates(
            self, cleaned, context, *, original=None, correction=None
        ):
            self.calls += 1
            if self.calls == 1:
                planned = stub_architect_result(
                    render_strategy="preserved_product_composite"
                )
                self.scene_prompt = planned.candidates[0].final_prompt
                broken = tuple(
                    replace(
                        item,
                        has_product_placement=False,
                        product_placement=None,
                    )
                    for item in planned.candidates
                )
                return PromptArchitectResult(
                    reference_summary=planned.reference_summary,
                    candidates=broken,
                )
            return await self._inner.plan_candidates(
                cleaned, context, original=original, correction=correction
            )

    async def run() -> None:
        set_cutout(PunchCutout())
        fake = FakeImageProvider()
        architect = FlipArchitect()
        result = await generate_recipe_set(
            recipe=recipe_from_ids(
                "photoreal_commercial", "product_pedestal", source="eval_fixed"
            ),
            reference=_jpeg(color=(180, 20, 20)),
            campaign=SimpleNamespace(visual_style="luxury"),
            concept=None,
            planner_context=PlannerContext(
                product_name="کرم",
                description=None,
                brand_name=None,
                price_text=None,
                audience=None,
                objective="sell_product",
                visual_style="luxury",
            ),
            provider=fake,
            planner=None,
            n=1,
            analysis=_isolatable_analysis(),
            product_type="cosmetics",
            category="cosmetics",
            architect=architect,
        )
        assert architect.calls == 2
        assert result.error is None
        assert result.architect["validation"]["ok"] is True
        assert result.architect["validation"]["retry_used"] is True
        assert result.architect["validation"]["switched_to_transform"] is True
        assert result.render_strategy == "reference_transform"
        assert fake.calls[0].references != ()
        assert fake.calls[0].prompt != architect.scene_prompt
        assert "this exact seller product" in fake.calls[0].prompt
        assert "no product drawn" not in fake.calls[0].prompt

    import asyncio

    asyncio.run(run())


def test_validation_failure_after_retry_makes_zero_image_calls() -> None:
    from types import SimpleNamespace

    from app.providers.vision.base import PlannerContext
    from app.services.campaigns.creative_core import generate_recipe_set
    from app.services.campaigns.recipes import recipe_from_ids
    from tests.fakes import FakeImageProvider

    class BadArchitect:
        name = "bad"
        model = None
        calls = 0

        async def plan_candidates(
            self, cleaned, context, *, original=None, correction=None
        ):
            del cleaned, context, original, correction
            self.calls += 1
            planned = stub_architect_result()
            from dataclasses import replace

            oversize = "this exact product sits on a table. " * 40
            return replace(
                planned,
                candidates=tuple(
                    replace(item, final_prompt=oversize[:900])
                    for item in planned.candidates
                ),
            )

    async def run() -> None:
        fake = FakeImageProvider()
        architect = BadArchitect()
        result = await generate_recipe_set(
            recipe=recipe_from_ids(
                "fashion_editorial", "model_using", source="eval_fixed"
            ),
            reference=_jpeg(),
            campaign=SimpleNamespace(visual_style="friendly"),
            concept=None,
            planner_context=PlannerContext(
                product_name="هودی",
                description=None,
                brand_name=None,
                price_text=None,
                audience=None,
                objective="sell_product",
                visual_style="friendly",
            ),
            provider=fake,
            planner=None,
            n=1,
            architect=architect,
        )
        assert architect.calls == 2
        assert result.error
        assert "exceeds 800" in result.error
        assert fake.calls == []
        assert result.architect["validation"]["ok"] is False
        assert result.architect["validation"]["retry_used"] is True

    import asyncio

    asyncio.run(run())


def test_implausible_composite_does_not_reuse_scene_prompt() -> None:
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import patch

    from app.providers.image.base import ImageResult, ImageUsage
    from app.providers.vision.base import PlannerContext
    from app.services.campaigns.creative_core import generate_recipe_set
    from app.services.campaigns.recipes import recipe_from_ids
    from tests.fakes import FakeImageProvider

    async def run() -> None:
        set_cutout(PunchCutout())
        fake = FakeImageProvider()
        scene = io.BytesIO()
        Image.new("RGB", (400, 500), (30, 120, 40)).save(scene, format="JPEG")
        fake.results = [
            ImageResult(
                content=scene.getvalue(),
                media_type="image/jpeg",
                usage=ImageUsage(latency_ms=4, cost_usd=Decimal("0"), model="fake"),
            )
        ]
        with patch(
            "app.services.campaigns.creative_core.composite_looks_plausible",
            return_value=False,
        ):
            result = await generate_recipe_set(
                recipe=recipe_from_ids(
                    "photoreal_commercial", "product_pedestal", source="eval_fixed"
                ),
                reference=_jpeg(color=(180, 20, 20)),
                campaign=SimpleNamespace(visual_style="luxury"),
                concept=None,
                planner_context=PlannerContext(
                    product_name="کرم",
                    description=None,
                    brand_name=None,
                    price_text=None,
                    audience=None,
                    objective="sell_product",
                    visual_style="luxury",
                ),
                provider=fake,
                planner=None,
                n=1,
                analysis=_isolatable_analysis(),
                product_type="cosmetics",
                category="cosmetics",
            )
        assert len(fake.calls) == 1
        assert fake.calls[0].references == ()
        assert "no product drawn" in fake.calls[0].prompt
        assert result.candidates[0].hard_failed
        assert (
            "composite could not plausibly integrate"
            in (result.candidates[0].quality or {}).get("reasons", [""])[-1]
        )

    import asyncio

    asyncio.run(run())
