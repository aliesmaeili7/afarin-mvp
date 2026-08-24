"""
Crop derivatives and cutouts. The original upload is never overwritten.
"""

from __future__ import annotations

import io
import logging
import uuid

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Campaign, CampaignAsset, CampaignConcept, ProductImage
from app.services.campaigns.crop import (
    CropRect,
    apply_crop,
    is_material_crop_change,
    parse_crop,
    suggest_crop,
)
from app.services.campaigns.cutout import get_cutout, rembg_available
from app.services.storage import (
    get_storage,
    is_public,
    parse,
    product_clean_reference_key,
    product_crop_key,
    product_cutout_key,
)
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)


async def assign_suggested_crop(
    session: AsyncSession,
    campaign: Campaign,
    image: ProductImage,
    original_bytes: bytes,
) -> None:
    if is_public(image.storage_path):
        image.crop_json = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        return
    rect = suggest_crop(original_bytes)
    await save_crop(session, campaign, image, rect, original_bytes=original_bytes)


async def save_crop(
    session: AsyncSession,
    campaign: Campaign,
    image: ProductImage,
    rect: CropRect,
    *,
    original_bytes: bytes | None = None,
) -> None:
    image.crop_json = rect.to_dict()
    if is_public(image.storage_path):
        image.crop_storage_path = None
        await _delete_cutout(session, campaign.id)
        await _clear_clean_reference(image)
        return

    source = original_bytes or await _download(image.storage_path)
    if source is None:
        logger.warning("could not read original upload to write crop")
        return

    jpeg = apply_crop(source, rect)
    settings = get_settings()
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=product_crop_key(campaign.id, image.id),
    )
    await get_storage().upload(ref, jpeg, "image/jpeg")
    image.crop_storage_path = ref.to_path()
    await _delete_cutout(session, campaign.id)
    await _clear_clean_reference(image)
    await _maybe_invalidate_director(session, campaign, rect)
    await session.flush()


async def primary_image(
    session: AsyncSession, campaign: Campaign
) -> ProductImage | None:
    images = await _images(session, campaign)
    if not images:
        return None
    return next((image for image in images if image.is_primary), images[0])


async def load_original_bytes(
    session: AsyncSession, campaign: Campaign
) -> bytes | None:
    image = await primary_image(session, campaign)
    if image is None or is_public(image.storage_path):
        return None
    return await _download(image.storage_path)


async def load_reference_bytes(
    session: AsyncSession, campaign: Campaign
) -> tuple[bytes | None, str | None]:
    """Crop JPEG when present; never the uncropped screenshot."""
    primary = await primary_image(session, campaign)
    if primary is None:
        return None, None
    path = primary.crop_storage_path or (
        primary.storage_path if is_public(primary.storage_path) else None
    )
    if path is None:
        return None, None
    if is_public(path):
        buffer = io.BytesIO()
        Image.new("RGB", (320, 400), (180, 140, 90)).save(buffer, format="JPEG")
        return buffer.getvalue(), path
    data = await _download(path)
    return data, path


async def load_creative_reference_bytes(
    session: AsyncSession, campaign: Campaign
) -> tuple[bytes | None, str | None]:
    """Cleaned JPEG only. Never the original upload."""
    primary = await primary_image(session, campaign)
    if primary is None:
        return None, None
    path = primary.clean_reference_storage_path
    if not path and is_public(primary.storage_path):
        return await load_reference_bytes(session, campaign)
    if not path:
        return None, None
    data = await _download(path)
    return data, path


async def store_clean_reference(
    session: AsyncSession,
    campaign: Campaign,
    jpeg: bytes,
) -> str:
    primary = await primary_image(session, campaign)
    if primary is None:
        raise RuntimeError("no product image for clean reference")
    settings = get_settings()
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=product_clean_reference_key(campaign.id, primary.id),
    )
    await get_storage().upload(ref, jpeg, "image/jpeg")
    primary.clean_reference_storage_path = ref.to_path()
    await session.flush()
    return ref.to_path()


async def prepare_product_layer(
    session: AsyncSession, campaign: Campaign
) -> tuple[str | None, str]:
    """
    Returns (storage_path, source) where source is cutout | crop | original.

    Never silently pastes a full screenshot as a cutout. If rembg is missing
    the seller-approved crop is used instead.
    """
    images = await _images(session, campaign)
    if not images:
        return None, "original"
    primary = next((image for image in images if image.is_primary), images[0])

    if is_public(primary.storage_path):
        return primary.storage_path, "original"

    crop_path = primary.crop_storage_path
    if not crop_path:
        source = await _download(primary.storage_path)
        if source is not None:
            try:
                rect = parse_crop(primary.crop_json)
            except ValueError:
                rect = suggest_crop(source)
            await save_crop(session, campaign, primary, rect, original_bytes=source)
            crop_path = primary.crop_storage_path

    cutout_path = await _ensure_cutout(session, campaign, primary, crop_path)
    if cutout_path:
        return cutout_path, "cutout"
    if crop_path:
        if not rembg_available():
            logger.warning(
                "rembg is not installed; compositing the crop, not the full upload"
            )
        else:
            logger.warning(
                "cutout failed; compositing the approved crop, not the full upload"
            )
        return crop_path, "crop"
    logger.warning("no crop derivative; refusing to treat the full upload as a cutout")
    return crop_path, "crop"


async def _ensure_cutout(
    session: AsyncSession,
    campaign: Campaign,
    primary: ProductImage,
    crop_path: str | None,
) -> str | None:
    existing = await session.scalar(
        select(CampaignAsset).where(
            CampaignAsset.campaign_id == campaign.id,
            CampaignAsset.asset_type == "product_cutout",
        )
    )
    if existing and existing.storage_path:
        return existing.storage_path

    if not crop_path:
        return None
    source = await _download(crop_path)
    if source is None:
        return None

    png = await get_cutout().remove_background(source)
    if not png:
        return None

    settings = get_settings()
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=product_cutout_key(campaign.id, primary.id),
    )
    await get_storage().upload(ref, png, "image/png")
    try:
        size = Image.open(io.BytesIO(png)).size
    except Exception:
        size = (1, 1)

    session.add(
        CampaignAsset(
            campaign_id=campaign.id,
            asset_type="product_cutout",
            storage_path=ref.to_path(),
            width=size[0],
            height=size[1],
            template_id=None,
            metadata_json={
                "source_product_image_id": str(primary.id),
                "from_crop": bool(crop_path),
            },
        )
    )
    await session.flush()
    return ref.to_path()


async def _delete_cutout(session: AsyncSession, campaign_id: uuid.UUID) -> None:
    await session.execute(
        delete(CampaignAsset).where(
            CampaignAsset.campaign_id == campaign_id,
            CampaignAsset.asset_type == "product_cutout",
        )
    )


async def _clear_clean_reference(image: ProductImage) -> None:
    image.clean_reference_storage_path = None


async def _maybe_invalidate_director(
    session: AsyncSession, campaign: Campaign, rect: CropRect
) -> None:
    snapshot = campaign.planner_result_json or {}
    previous = snapshot.get("analyzed_crop")
    if not previous or campaign.status not in ("concepts_ready", "concept_selected"):
        return
    try:
        old = parse_crop(previous)
    except ValueError:
        return
    if not is_material_crop_change(old, rect):
        return
    await session.execute(
        delete(CampaignConcept).where(CampaignConcept.campaign_id == campaign.id)
    )
    campaign.selected_concept_id = None
    campaign.concept_round = None
    campaign.planner_result_json = {}
    campaign.visual_recipe_json = {}
    if campaign.product_id and campaign.objective and campaign.visual_style:
        campaign.status = "brief_complete"
    else:
        campaign.status = "draft"


async def _images(session: AsyncSession, campaign: Campaign) -> list[ProductImage]:
    if campaign.product_id is None:
        return []
    rows = await session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == campaign.product_id)
        .order_by(ProductImage.created_at)
    )
    return list(rows)


async def _download(storage_path: str) -> bytes | None:
    ref = parse(storage_path)
    if ref is None:
        return None
    return await get_storage().download(ref)
