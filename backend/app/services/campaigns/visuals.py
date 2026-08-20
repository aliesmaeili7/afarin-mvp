"""
Empty-scene generation and local product cutout.

Two paid backgrounds per campaign (4:5 and 9:16). Finals keep storage_path
null so AdCanvas still draws Persian type (Phase 5 is baked export).
"""

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import FEED_SCENE_TYPES, STORY_SCENE_TYPES, VISUAL_FINAL_TYPES
from app.db.models import Campaign, CampaignAsset, CampaignConcept
from app.providers.image import get_image_provider
from app.providers.image.base import (
    ImageApiError,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.prompts import build_scene_prompt
from app.services.campaigns import queries
from app.services.campaigns.product_media import prepare_product_layer
from app.services.storage import get_storage, scene_image_key
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)

SCENE_4X5 = (1080, 1350)
SCENE_9X16 = (1080, 1920)

ASPECT_4X5 = "4:5"
ASPECT_9X16 = "9:16"


@dataclass(frozen=True, slots=True)
class _Scene:
    result: ImageResult
    storage_path: str


async def attach_visuals(
    session: AsyncSession, campaign: Campaign
) -> tuple[str, ImageUsage | None, list[dict]]:
    """
    Cut out the product locally, generate two empty scenes, and wire them onto
    the five finals. Copy rows are left untouched.
    """
    selected = await _selected_concept(session, campaign)
    product_path, product_source = await prepare_product_layer(session, campaign)
    prompt = build_scene_prompt(selected, campaign)
    failures: list[dict] = []

    feed = await _generate_scene(
        session, campaign, ASPECT_4X5, prompt, variation=0, failures=failures
    )
    story = await _generate_scene(
        session, campaign, ASPECT_9X16, prompt, variation=0, failures=failures
    )

    await _apply_scene(
        session,
        campaign,
        scene=feed,
        product_path=product_path,
        product_source=product_source,
        types=FEED_SCENE_TYPES,
    )
    await _apply_scene(
        session,
        campaign,
        scene=story,
        product_path=product_path,
        product_source=product_source,
        types=STORY_SCENE_TYPES,
    )

    failed = await failed_visual_types(session, campaign.id)
    if failed:
        campaign.status = "partial_failed"
    else:
        campaign.status = "ready"
    await session.flush()
    succeeded = [item.result for item in (feed, story) if item is not None]
    usage = combined_usage(succeeded) if succeeded else None
    return campaign.status, usage, failures


async def regenerate_scene(
    session: AsyncSession,
    campaign: Campaign,
    *,
    aspect: str,
    variation: int,
) -> ImageUsage | None:
    """Replace one scene. Feed and carousel share 4:5; story is 9:16."""
    selected = await _selected_concept(session, campaign)
    prompt = build_scene_prompt(selected, campaign, variation=variation)
    scene = await _generate_scene(
        session,
        campaign,
        aspect,
        prompt,
        variation=variation,
        swallow=False,
    )
    if scene is None:
        return None
    product_path, product_source = await prepare_product_layer(session, campaign)
    types = FEED_SCENE_TYPES if aspect == ASPECT_4X5 else STORY_SCENE_TYPES
    await _apply_scene(
        session,
        campaign,
        scene=scene,
        product_path=product_path,
        product_source=product_source,
        types=types,
    )
    failed = await failed_visual_types(session, campaign.id)
    if campaign.status == "partial_failed" and not failed:
        campaign.status = "ready"
    await session.flush()
    return scene.result.usage


async def failed_visual_types(
    session: AsyncSession, campaign_id: uuid.UUID
) -> list[str]:
    assets = await queries.assets_of(session, campaign_id)
    return [
        asset.asset_type
        for asset in assets
        if asset.asset_type in VISUAL_FINAL_TYPES
        and (asset.metadata_json or {}).get("failed")
    ]


def combined_usage(results: list[ImageResult]) -> ImageUsage:
    cost: Decimal | None = None
    latency = 0
    model: str | None = None
    prompt_tokens = 0
    completion_tokens = 0
    has_prompt = False
    has_completion = False
    for result in results:
        usage = result.usage
        latency += usage.latency_ms
        if usage.cost_usd is not None:
            cost = (cost or Decimal("0")) + usage.cost_usd
        if usage.model:
            model = usage.model
        if usage.prompt_tokens is not None:
            prompt_tokens += usage.prompt_tokens
            has_prompt = True
        if usage.completion_tokens is not None:
            completion_tokens += usage.completion_tokens
            has_completion = True
    return ImageUsage(
        latency_ms=latency,
        cost_usd=cost,
        model=model,
        prompt_tokens=prompt_tokens if has_prompt else None,
        completion_tokens=completion_tokens if has_completion else None,
    )


async def _generate_scene(
    session: AsyncSession,
    campaign: Campaign,
    aspect: str,
    prompt: str,
    *,
    variation: int,
    failures: list[dict] | None = None,
    swallow: bool = True,
) -> _Scene | None:
    provider = get_image_provider()
    width, height = SCENE_9X16 if aspect == ASPECT_9X16 else SCENE_4X5
    settings = get_settings()
    try:
        result = await provider.generate(
            ImageRequest(
                prompt=prompt,
                aspect_ratio=aspect,
                resolution=settings.image_resolution,
            )
        )
    except ImageApiError as error:
        logger.warning(
            "scene generation failed aspect=%s status=%s retryable=%s message=%s",
            aspect,
            error.status_code,
            error.retryable,
            error.provider_message,
        )
        if failures is not None:
            failures.append(error.to_dict())
        if not swallow:
            raise
        return None
    except Exception:
        logger.exception("scene generation failed aspect=%s", aspect)
        if not swallow:
            raise
        return None

    jpeg = _as_jpeg(result.content)
    token = uuid.uuid4().hex[:12]
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=scene_image_key(campaign.id, aspect, token),
    )
    await get_storage().upload(ref, jpeg, "image/jpeg")

    await session.execute(
        delete(CampaignAsset).where(
            CampaignAsset.campaign_id == campaign.id,
            CampaignAsset.asset_type == "generated_background",
            CampaignAsset.width == width,
            CampaignAsset.height == height,
        )
    )
    session.add(
        CampaignAsset(
            campaign_id=campaign.id,
            asset_type="generated_background",
            storage_path=ref.to_path(),
            width=width,
            height=height,
            template_id=None,
            metadata_json={"aspect": aspect, "variation": variation},
        )
    )
    await session.flush()
    return _Scene(
        result=ImageResult(content=jpeg, media_type="image/jpeg", usage=result.usage),
        storage_path=ref.to_path(),
    )


async def _apply_scene(
    session: AsyncSession,
    campaign: Campaign,
    *,
    scene: _Scene | None,
    product_path: str | None,
    product_source: str,
    types: tuple[str, ...],
) -> None:
    assets = await session.scalars(
        select(CampaignAsset).where(
            CampaignAsset.campaign_id == campaign.id,
            CampaignAsset.asset_type.in_(types),
        )
    )
    for asset in assets:
        spec = dict(asset.metadata_json or {})
        spec["product_image_path"] = product_path
        spec["product_source"] = product_source
        if scene is not None:
            spec["scene_image_path"] = scene.storage_path
            spec["failed"] = False
        else:
            spec["failed"] = True
        asset.metadata_json = spec
    await session.flush()


async def _selected_concept(
    session: AsyncSession, campaign: Campaign
) -> CampaignConcept | None:
    if campaign.selected_concept_id is None:
        return None
    return await session.scalar(
        select(CampaignConcept).where(
            CampaignConcept.id == campaign.selected_concept_id
        )
    )


def _as_jpeg(content: bytes) -> bytes:
    if content.startswith(b"\xff\xd8"):
        return content
    image = Image.open(io.BytesIO(content)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
