"""
The dashboard card contract.

A finished campaign is represented by its feed ad, not by the photo the seller
uploaded, so the dashboard shows what they actually made. Computed server side
here with exactly the rule thumbnailOf used in Phase 1.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign, CampaignAsset
from app.schemas.domain import CampaignSummaryOut
from app.services.campaigns import materialize as materializer
from app.services.campaigns import queries


async def ensure_materialized(session: AsyncSession, campaign: Campaign) -> None:
    """
    A campaign can be marked ready before its rows exist — the seeded sample is
    the case that matters. The card needs the feed ad to preview.
    """
    if campaign.status not in ("ready", "partial_failed"):
        return
    has_assets = await session.scalar(
        select(CampaignAsset.id)
        .where(CampaignAsset.campaign_id == campaign.id)
        .limit(1)
    )
    if has_assets is None:
        await materializer.materialize(
            session, campaign, partial_failure=campaign.status == "partial_failed"
        )


async def summarize(session: AsyncSession, campaign: Campaign) -> CampaignSummaryOut:
    product = await queries.product_of(session, campaign)
    brand = await queries.brand_of(session, campaign)

    feed = await session.scalar(
        select(CampaignAsset).where(
            CampaignAsset.campaign_id == campaign.id,
            CampaignAsset.asset_type == "feed_final",
        )
    )
    spec: dict[str, Any] | None = feed.metadata_json if feed else None

    thumbnail_path = (feed.storage_path if feed else None) or (
        await queries.primary_image_path(session, campaign)
    )
    product_name = (product.name or "").strip() if product else ""

    return CampaignSummaryOut(
        id=campaign.id,
        product_name=product_name or None,
        brand_name=brand.name if brand else None,
        status=campaign.status,
        thumbnail_path=thumbnail_path,
        # Null until a real headline exists, so the card falls back to the photo
        # rather than rendering an empty ad.
        thumbnail_spec=spec if spec and spec.get("headline_fa") else None,
        created_at=campaign.created_at,
    )
