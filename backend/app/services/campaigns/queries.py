"""Shared reads. Keeps the routers free of query construction."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.context import CopyContext
from app.db.models import (
    Brand,
    Campaign,
    CampaignAsset,
    CampaignConcept,
    CampaignCopy,
    Product,
    ProductImage,
)


async def product_of(session: AsyncSession, campaign: Campaign) -> Product | None:
    if campaign.product_id is None:
        return None
    return await session.scalar(
        select(Product).where(Product.id == campaign.product_id)
    )


async def brand_of(session: AsyncSession, campaign: Campaign) -> Brand | None:
    if campaign.brand_id is None:
        return None
    return await session.scalar(select(Brand).where(Brand.id == campaign.brand_id))


async def images_of(session: AsyncSession, campaign: Campaign) -> list[ProductImage]:
    if campaign.product_id is None:
        return []
    rows = await session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == campaign.product_id)
        .order_by(ProductImage.created_at)
    )
    return list(rows)


async def primary_image_path(session: AsyncSession, campaign: Campaign) -> str | None:
    images = await images_of(session, campaign)
    if not images:
        return None
    primary = next((image for image in images if image.is_primary), images[0])
    return primary.storage_path


async def concepts_of(
    session: AsyncSession, campaign_id: uuid.UUID
) -> list[CampaignConcept]:
    rows = await session.scalars(
        select(CampaignConcept)
        .where(CampaignConcept.campaign_id == campaign_id)
        .order_by(CampaignConcept.concept_number)
    )
    return list(rows)


async def copies_of(
    session: AsyncSession, campaign_id: uuid.UUID
) -> list[CampaignCopy]:
    rows = await session.scalars(
        select(CampaignCopy)
        .where(CampaignCopy.campaign_id == campaign_id)
        .order_by(CampaignCopy.created_at)
    )
    return list(rows)


async def assets_of(
    session: AsyncSession, campaign_id: uuid.UUID
) -> list[CampaignAsset]:
    rows = await session.scalars(
        select(CampaignAsset)
        .where(CampaignAsset.campaign_id == campaign_id)
        .order_by(CampaignAsset.created_at)
    )
    return list(rows)


async def build_copy_context(session: AsyncSession, campaign: Campaign) -> CopyContext:
    product = await product_of(session, campaign)
    brand = await brand_of(session, campaign)
    name = (product.name or "").strip() if product else ""

    return CopyContext(
        product_name=name or "محصول شما",
        description=product.description if product else None,
        price_text=product.price_text if product else None,
        benefit=product.main_benefit if product else None,
        brand_name=brand.name if brand else None,
        audience=campaign.audience,
        objective=campaign.objective or "sell_product",
        style=campaign.visual_style or "modern",
        round=campaign.concept_round or 0,
    )
