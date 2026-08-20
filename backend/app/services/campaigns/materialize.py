"""
Produces the campaign output rows.

The single definition of "what a finished campaign contains", ported from
materializeCampaign in the Phase 1 mock. Phase 4 writes empty scenes and a
local product cutout, then AdCanvas composites them with Persian type.
`storage_path` on the five finals stays null until Phase 5 baked export.
"""

import uuid
from dataclasses import replace
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.backgrounds import backgrounds_for_style
from app.content.context import CopyContext
from app.db.models import Campaign, CampaignAsset, CampaignConcept, CampaignCopy
from app.providers.llm import get_content_provider
from app.services.campaigns import queries
from app.services.campaigns import visuals as visualizer


def concept_background_id(concept: CampaignConcept | None, campaign: Campaign) -> str:
    raw = (concept.raw_json or {}) if concept else {}
    background = raw.get("background_id")
    if isinstance(background, str) and background:
        return background
    return backgrounds_for_style(campaign.visual_style)[0]


async def write_concepts(
    session: AsyncSession, campaign: Campaign, ctx: CopyContext
) -> list[CampaignConcept]:
    drafts = await get_content_provider().build_concepts(ctx)

    await session.execute(
        delete(CampaignConcept).where(CampaignConcept.campaign_id == campaign.id)
    )

    created: list[CampaignConcept] = []
    for index, draft in enumerate(drafts):
        concept = CampaignConcept(
            campaign_id=campaign.id,
            concept_number=index + 1,
            title_fa=draft.title_fa,
            headline_fa=draft.headline_fa,
            description_fa=draft.description_fa,
            visual_direction=draft.visual_direction,
            background_prompt=draft.background_prompt,
            raw_json={"background_id": draft.background_id},
            selected=False,
        )
        session.add(concept)
        created.append(concept)

    await session.flush()
    return created


CONCEPT_INVALIDATION_STATUSES = ("concepts_ready", "concept_selected")


def blank_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def invalidate_concepts_if_stale(
    session: AsyncSession, campaign: Campaign, changed: bool
) -> None:
    """Drop generated ideas when the brief that produced them no longer holds."""
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


def _spec(
    base: dict[str, Any], overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {**base, "slide_label_fa": None, **(overrides or {})}


async def materialize(
    session: AsyncSession, campaign: Campaign, *, partial_failure: bool = False
) -> str:
    """
    Writes copy, asset specs and (when possible) real scenes.

    Called when a generation job completes, and lazily for the seeded sample, so
    there is exactly one definition of a finished campaign.
    """
    await materialize_copy(session, campaign, partial_failure=partial_failure)
    status, _usage, _failures = await visualizer.attach_visuals(session, campaign)
    return status


async def materialize_copy(
    session: AsyncSession, campaign: Campaign, *, partial_failure: bool = False
) -> None:
    """
    Commits Persian copy and five AssetRenderSpecs. Does not call an image
    model, so a later visual failure can keep this text.
    """
    provider = get_content_provider()
    ctx = await queries.build_copy_context(session, campaign)

    concepts = await queries.concepts_of(session, campaign.id)
    if not concepts:
        concepts = await write_concepts(session, campaign, ctx)

    selected = next((concept for concept in concepts if concept.selected), None)
    if selected is None:
        selected = concepts[0]
        selected.selected = True
        campaign.selected_concept_id = selected.id

    ctx = replace(ctx, selected_headline=selected.headline_fa)

    await session.execute(
        delete(CampaignCopy).where(CampaignCopy.campaign_id == campaign.id)
    )

    captions = await provider.build_captions(ctx)
    _add_copy(session, campaign.id, "caption_short", captions.caption_short)
    _add_copy(session, campaign.id, "caption_friendly", captions.caption_friendly)
    _add_copy(session, campaign.id, "caption_persuasive", captions.caption_persuasive)

    for order, story in enumerate(await provider.build_story_ideas(ctx)):
        _add_copy(session, campaign.id, "story", story, {"order": order})

    primary_cta = await provider.build_primary_cta(ctx)
    _add_copy(session, campaign.id, "cta", primary_cta)
    _add_copy(session, campaign.id, "hashtags", await provider.build_hashtags(ctx))

    reel = await provider.build_reel_concept(ctx)
    _add_copy(
        session, campaign.id, "reel_concept", reel.hook_fa, {"reel": reel.to_dict()}
    )

    brand = await queries.brand_of(session, campaign)
    base: dict[str, Any] = {
        "template_id": "feed_classic",
        "background_id": concept_background_id(selected, campaign),
        "headline_fa": selected.headline_fa,
        "subheadline_fa": await provider.build_subheadline(ctx),
        "cta_fa": primary_cta,
        "price_text": ctx.price_text,
        "brand_name": brand.name if brand else ctx.brand_name,
        "product_image_path": await queries.primary_image_path(session, campaign),
        "scene_image_path": None,
    }

    await session.execute(
        delete(CampaignAsset).where(CampaignAsset.campaign_id == campaign.id)
    )

    _add_asset(session, campaign.id, "feed_final", 1080, 1350, _spec(base))

    # A partial failure keeps the row so the seller can retry just that asset.
    _add_asset(
        session,
        campaign.id,
        "story_final",
        1080,
        1920,
        _spec(base, {"template_id": "story_classic", "failed": partial_failure}),
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
                "headline_fa": ctx.benefit or ctx.description or "چرا این محصول؟",
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
                "headline_fa": primary_cta,
                "subheadline_fa": ctx.price_text or ctx.product_name,
                "slide_label_fa": "۳",
            },
        ),
    )

    await session.flush()


def _add_copy(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    copy_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        CampaignCopy(
            campaign_id=campaign_id,
            copy_type=copy_type,
            content=content,
            metadata_json=metadata or {},
        )
    )


def _add_asset(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    asset_type: str,
    width: int,
    height: int,
    spec: dict[str, Any],
) -> None:
    session.add(
        CampaignAsset(
            campaign_id=campaign_id,
            asset_type=asset_type,
            # Finals stay path-less so AdCanvas keeps drawing type (Phase 5).
            storage_path=None,
            width=width,
            height=height,
            template_id=spec["template_id"],
            metadata_json=spec,
        )
    )
