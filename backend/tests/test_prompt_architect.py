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
from app.providers.image.creative_prompts import (
    SAFETY_SUFFIX,
    compile_architect_result,
    compile_creative_prompt,
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
from app.providers.image import set_image_provider


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
                if x < margin or y < margin or x >= width - margin or y >= height - margin:
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
    recipe = recipe_from_ids(
        "fashion_editorial", "hero_product", source="custom"
    )
    assert recipe["compatibility"] == "discouraged"
    assert recipe["warning_fa"] == DISCOURAGED_WARNING_FA


def test_stub_director_is_not_forced_surreal() -> None:
    ids = {(item.style_id, item.template_id) for item in SMART_DIRECTIONS}
    assert ("photoreal_commercial", "hero_product") in ids
    assert ("photoreal_commercial", "model_using") in ids
    assert ("surreal", "giant_miniature_world") not in ids


def test_compiler_appends_safety_suffix() -> None:
    compiled = compile_architect_result(stub_architect_result())
    assert len(compiled.candidates) == 3
    prompts = [item.compiled_prompt for item in compiled.candidates]
    assert len(set(prompts)) == 3
    for prompt in prompts:
        assert SAFETY_SUFFIX in prompt
        assert "4:5 Instagram advertisement still" in prompt
    raw = compile_creative_prompt(stub_architect_result().candidates[0])
    assert raw.endswith("4:5 Instagram advertisement still") or SAFETY_SUFFIX in raw


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
    assert decide_strategy({"person_present": True, "reference_strategy": "subject_cutout_neutral"}) == (
        "preserve_context_crop"
    )


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
                select(ProductImage).where(ProductImage.product_id == campaign.product_id)
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
                select(GenerationJob).where(
                    GenerationJob.campaign_id == campaign.id
                )
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
