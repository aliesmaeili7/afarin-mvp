"""
Produces the campaign output rows.

Copy comes from the Unified Creative Agent. This module writes AssetRenderSpecs
and fixture helpers. `storage_path` on the five finals stays null until Phase 5.
"""

from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.backgrounds import backgrounds_for_style
from app.db.models import Campaign, CampaignAsset, CampaignConcept, CampaignCopy
from app.services.campaigns import queries


def blank_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


CONCEPT_INVALIDATION_STATUSES = ("concepts_ready", "concept_selected")


async def invalidate_concepts_if_stale(
    session: AsyncSession, campaign: Campaign, changed: bool
) -> None:
    if not changed or campaign.status not in CONCEPT_INVALIDATION_STATUSES:
        return
    await session.execute(
        delete(CampaignConcept).where(CampaignConcept.campaign_id == campaign.id)
    )
    campaign.selected_concept_id = None
    campaign.concept_round = None
    if campaign.product_id and campaign.objective and campaign.visual_style:
        campaign.status = "brief_complete"
    else:
        campaign.status = "draft"


def _spec(base: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    return {**base, "slide_label_fa": None, **(overrides or {})}


async def write_package_assets(
    session: AsyncSession,
    campaign: Campaign,
    headline: str,
    cta: str,
    secondary: str | None = None,
) -> None:
    ctx = await queries.build_copy_context(session, campaign)
    brand = await queries.brand_of(session, campaign)
    base: dict[str, Any] = {
        "template_id": "feed_classic",
        "background_id": backgrounds_for_style(campaign.visual_style)[0],
        "headline_fa": headline,
        "subheadline_fa": secondary,
        "cta_fa": cta,
        "price_text": ctx.price_text,
        "brand_name": brand.name if brand else ctx.brand_name,
        "product_image_path": None,
        "scene_image_path": None,
        "product_source": "generated",
        "visual_mode": "creative",
    }
    await session.execute(
        delete(CampaignAsset).where(CampaignAsset.campaign_id == campaign.id)
    )
    _add_asset(session, campaign.id, "feed_final", 1080, 1350, _spec(base))
    _add_asset(
        session,
        campaign.id,
        "story_final",
        1080,
        1920,
        _spec(base, {"template_id": "story_classic"}),
    )
    _add_asset(
        session,
        campaign.id,
        "carousel_1",
        1080,
        1350,
        _spec(base, {"template_id": "carousel_hook", "slide_label_fa": "۱"}),
    )
    _add_asset(
        session,
        campaign.id,
        "carousel_2",
        1080,
        1350,
        _spec(
            base,
            {
                "template_id": "carousel_benefit",
                "headline_fa": ctx.benefit or ctx.description or headline,
                "subheadline_fa": ctx.product_name,
                "slide_label_fa": "۲",
            },
        ),
    )
    _add_asset(
        session,
        campaign.id,
        "carousel_3",
        1080,
        1350,
        _spec(
            base,
            {
                "template_id": "carousel_cta",
                "headline_fa": cta,
                "subheadline_fa": ctx.price_text or ctx.product_name,
                "slide_label_fa": "۳",
            },
        ),
    )
    await session.flush()


async def materialize(
    session: AsyncSession, campaign: Campaign, *, partial_failure: bool = False
) -> str:
    del partial_failure
    assets = await queries.assets_of(session, campaign.id)
    if not assets:
        await write_package_assets(session, campaign, "محصول", "سفارش بده")
    return campaign.status


def _add_asset(
    session: AsyncSession,
    campaign_id,
    asset_type: str,
    width: int,
    height: int,
    spec: dict[str, Any],
) -> None:
    session.add(
        CampaignAsset(
            campaign_id=campaign_id,
            asset_type=asset_type,
            storage_path=None,
            width=width,
            height=height,
            template_id=spec["template_id"],
            metadata_json=spec,
        )
    )
