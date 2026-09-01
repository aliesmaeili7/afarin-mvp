"""Unified Creative Agent production generation."""

from __future__ import annotations

import io
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.visual_catalog import catalog_digest, template_semantics
from app.core import messages
from app.core.config import get_settings
from app.core.enums import FEED_SCENE_TYPES, STORY_SCENE_TYPES
from app.core.errors import generation_failed, invalid, not_found
from app.db.models import (
    Campaign,
    CampaignAsset,
    CampaignCopy,
    CampaignVisualAttempt,
    CampaignVisualCandidate,
    GenerationJob,
)
from app.providers.image import get_image_provider
from app.providers.image.base import ImageApiError, ImageRequest, ImageResult, ImageUsage
from app.providers.image.creative_prompts import build_repair_prompt
from app.providers.vision import get_creative_agent
from app.providers.vision.base import (
    CandidateQuality,
    CreativeAgentContext,
    QualityContext,
    QualityReport,
)
from app.services.campaigns import cost as budgets
from app.services.campaigns import jobs as job_records
from app.services.campaigns import queries
from app.services.campaigns.creative_core import generate_recipe_set
from app.services.campaigns.stages import set_job_stage
from app.services.campaigns.product_media import (
    load_creative_reference_bytes,
    load_original_bytes,
    load_reference_bytes,
    store_clean_reference,
)
from app.services.campaigns.reference_prep import (
    MIN_REFERENCE_PX,
    assert_not_blocked,
    prepare_clean_jpeg,
)
from app.services.storage import get_storage, visual_candidate_key
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)

ASPECT_4X5 = "4:5"


async def generate_candidates(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    *,
    source: str = "smart",
) -> None:
    await budgets.assert_can_start_attempt(session, campaign)
    cleaned = await _require_clean_reference(session, campaign)
    context = await agent_context_for(session, campaign)
    source = "custom" if context.template_id or context.visual_instruction else "smart"

    used = await budgets.attempt_count(session, campaign.id)
    attempt = CampaignVisualAttempt(
        campaign_id=campaign.id,
        attempt_number=used + 1,
        source=source if source in ("smart", "custom") else "custom",
        recipe_json={
            "template_id": context.template_id,
            "visual_instruction": context.visual_instruction,
            "requested_image_count": context.requested_image_count,
        },
        planner_json={},
        status="generating",
        auto_repair_used=False,
    )
    session.add(attempt)
    await session.flush()

    previous = await session.scalar(
        select(CampaignVisualAttempt).where(
            CampaignVisualAttempt.id == campaign.current_visual_attempt_id
        )
    )
    if previous is not None and previous.status in ("awaiting_selection", "selected"):
        previous.status = "superseded"

    campaign.current_visual_attempt_id = attempt.id
    set_job_stage(job, "planning")
    await session.flush()
    started_perf = time.perf_counter()

    agent_job = await _run_agent_job(session, campaign, attempt, job.user_id, context)

    async def on_stage(stage: str) -> None:
        set_job_stage(job, stage)
        await session.commit()

    out = await generate_recipe_set(
        context=context,
        reference=cleaned,
        provider=get_image_provider(),
        agent=get_creative_agent(),
        quality_check=True,
        repair="production",
        timestamp=datetime.now(UTC).isoformat(),
        on_stage=on_stage,
    )
    wall_ms = int(round((time.perf_counter() - started_perf) * 1000))
    payload = dict(out.creative_agent or {})
    payload["wall_time_ms"] = wall_ms
    payload["requested_image_count"] = context.requested_image_count
    payload["successful_image_count"] = out.successful_image_count
    payload["validation"] = (out.creative_agent or {}).get("validation") or {}
    attempt.creative_agent_json = payload
    if agent_job is not None and out.creative_agent:
        usage = (out.creative_agent or {}).get("usage") or {}
        if usage:
            from app.providers.llm.base import LlmUsage

            cost = usage.get("cost_usd")
            job_records.apply_llm_usage(
                agent_job,
                LlmUsage(
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    latency_ms=usage.get("latency_ms"),
                    cost_usd=Decimal(cost) if cost else None,
                    model=usage.get("model"),
                ),
            )
        if out.error:
            job_records.mark_failed(agent_job, generation_failed())
        else:
            job_records.mark_succeeded(
                agent_job,
                {
                    "image_count": context.requested_image_count,
                    "validation": payload.get("validation"),
                },
                consume_llm=False,
            )

    if out.error:
        raise generation_failed()

    await _persist_copy(session, campaign, payload)
    n = len(out.candidates)
    await _record_image_budget(job, attempt.attempt_number, n)

    stored: list[CampaignVisualCandidate] = []
    for frame in out.candidates:
        stored.append(
            await _store_candidate(
                session,
                campaign,
                attempt,
                slot=frame.slot,
                jpeg=frame.jpeg,
                job_id=job.id,
                kind="primary",
                variation_index=frame.variation,
            )
        )
        if frame.quality:
            stored[-1].quality_json = frame.quality
            stored[-1].hard_failed = frame.hard_failed
            stored[-1].hidden = frame.hidden

    for repair in out.repairs:
        repaired = await _store_candidate(
            session,
            campaign,
            attempt,
            slot=repair.slot,
            jpeg=repair.jpeg,
            job_id=job.id,
            kind="repair",
            variation_index=repair.variation,
        )
        if repair.quality:
            repaired.quality_json = repair.quality
            repaired.hard_failed = repair.hard_failed
            repaired.hidden = repair.hidden
        if not repair.hard_failed:
            for row in stored:
                if row.slot == repair.slot and row.kind == "primary":
                    row.hidden = True
        attempt.auto_repair_used = True
        stored.append(repaired)

    visible = [row for row in stored if not row.hidden and not row.hard_failed]
    focused = visible[0] if visible else stored[0]
    attempt.selected_candidate_id = focused.id
    attempt.status = "selected"
    await _apply_focused(session, campaign, payload, focused)
    campaign.status = "ready"
    campaign.updated_at = datetime.now(UTC)
    await session.flush()


async def focus_concept(
    session: AsyncSession,
    campaign: Campaign,
    candidate_id: uuid.UUID,
) -> None:
    attempt = await _current_attempt(session, campaign)
    if attempt is None:
        raise invalid(messages.CANDIDATE_REQUIRED)
    candidate = await session.scalar(
        select(CampaignVisualCandidate).where(
            CampaignVisualCandidate.id == candidate_id,
            CampaignVisualCandidate.attempt_id == attempt.id,
        )
    )
    if candidate is None or candidate.hidden:
        raise not_found(messages.CANDIDATE_NOT_FOUND)
    attempt.selected_candidate_id = candidate.id
    attempt.status = "selected"
    campaign.status = "ready"
    campaign.updated_at = datetime.now(UTC)
    await _apply_focused(
        session, campaign, attempt.creative_agent_json or {}, candidate
    )
    await session.flush()


async def agent_context_for(
    session: AsyncSession, campaign: Campaign
) -> CreativeAgentContext:
    ctx = await queries.build_copy_context(session, campaign)
    template_id = campaign.selected_template_id
    count = campaign.requested_image_count or 1
    if count not in (1, 3):
        count = 1
    semantics = template_semantics(template_id) or {}
    return CreativeAgentContext(
        product_name=ctx.product_name,
        description=ctx.description,
        brand_name=ctx.brand_name,
        price_text=ctx.price_text,
        audience=ctx.audience,
        objective=ctx.objective or "sell_product",
        visual_style=ctx.style or campaign.visual_style or "modern",
        requested_image_count=count,
        template_id=template_id,
        template_semantics=semantics,
        visual_instruction=campaign.visual_instruction,
        catalog_digest=catalog_digest(),
    )


async def _run_agent_job(
    session: AsyncSession,
    campaign: Campaign,
    attempt: CampaignVisualAttempt,
    user_id,
    context: CreativeAgentContext,
) -> GenerationJob:
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="creative_agent",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "template_id": context.template_id,
            "requested_image_count": context.requested_image_count,
            "attempt_id": str(attempt.id),
        },
    )
    session.add(job)
    await session.flush()
    return job


async def _persist_copy(
    session: AsyncSession, campaign: Campaign, payload: dict
) -> None:
    from sqlalchemy import delete

    await session.execute(
        delete(CampaignCopy).where(CampaignCopy.campaign_id == campaign.id)
    )
    images = payload.get("images") or []
    for index, item in enumerate(images, start=1):
        copy = item.get("copy") or {}
        slot_meta = {"slot": index, "concept_title": item.get("concept_title")}
        _add_copy(
            session,
            campaign.id,
            "caption_persuasive",
            str(copy.get("feed_caption") or ""),
            slot_meta,
        )
        _add_copy(
            session, campaign.id, "story", str(copy.get("story_text") or ""), slot_meta
        )
        _add_copy(session, campaign.id, "cta", str(copy.get("cta") or ""), slot_meta)
        tags = copy.get("hashtags") or []
        hashtags = " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags)
        _add_copy(session, campaign.id, "hashtags", hashtags, slot_meta)
    await session.flush()


def _add_copy(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    copy_type: str,
    content: str,
    metadata: dict,
) -> None:
    if not content.strip():
        return
    session.add(
        CampaignCopy(
            campaign_id=campaign_id,
            copy_type=copy_type,
            content=content,
            metadata_json=metadata,
        )
    )


async def _apply_focused(
    session: AsyncSession,
    campaign: Campaign,
    payload: dict,
    candidate: CampaignVisualCandidate,
) -> None:
    images = payload.get("images") or []
    item = images[candidate.slot - 1] if 0 < candidate.slot <= len(images) else {}
    copy = item.get("copy") or {}
    plan = item.get("visual_plan") or {}
    safe = (plan.get("text_safe_area") or {}).get("position") or "bottom"
    headline = str(copy.get("on_image_headline") or "")
    secondary = copy.get("on_image_secondary")
    cta = str(copy.get("cta") or "")
    story_text = str(copy.get("story_text") or headline)
    path = candidate.storage_path
    brand = await queries.brand_of(session, campaign)
    ctx = await queries.build_copy_context(session, campaign)
    assets = await queries.assets_of(session, campaign.id)
    if not assets:
        from app.services.campaigns.materialize import write_package_assets

        await write_package_assets(session, campaign, headline, cta, secondary)
        assets = await queries.assets_of(session, campaign.id)
    for asset in assets:
        spec = dict(asset.metadata_json or {})
        spec["visual_mode"] = "creative"
        spec["product_image_path"] = None
        spec["product_source"] = "generated"
        spec["failed"] = False
        spec["text_safe_area"] = safe
        spec["concept_slot"] = candidate.slot
        spec["cta_fa"] = cta
        spec["price_text"] = ctx.price_text
        spec["brand_name"] = brand.name if brand else ctx.brand_name
        spec["scene_image_path"] = path
        if asset.asset_type in FEED_SCENE_TYPES:
            spec["headline_fa"] = headline
            if secondary:
                spec["subheadline_fa"] = secondary
            if asset.asset_type == "carousel_3":
                spec["headline_fa"] = cta
        elif asset.asset_type in STORY_SCENE_TYPES:
            spec["headline_fa"] = story_text
            spec["template_id"] = "story_classic"
        asset.metadata_json = spec
    await session.flush()


async def _record_image_budget(
    job: GenerationJob, attempt_number: int, n: int
) -> None:
    already = 0
    budgets.assert_role_budget("candidate", already, n)
    payload = dict(job.input_json or {})
    payload["mode"] = "creative"
    payload["attempt_number"] = attempt_number
    payload["aspect"] = ASPECT_4X5
    payload["role"] = "candidate"
    payload["n"] = n
    payload["output_count"] = n
    payload["output_counts"] = {"candidate": n}
    payload["roles"] = ["candidate"]
    job.input_json = payload


async def _store_candidate(
    session: AsyncSession,
    campaign: Campaign,
    attempt: CampaignVisualAttempt,
    *,
    slot: int,
    jpeg: bytes,
    job_id: uuid.UUID,
    kind: str,
    variation_index: int,
) -> CampaignVisualCandidate:
    settings = get_settings()
    token = uuid.uuid4().hex[:12]
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=visual_candidate_key(campaign.id, attempt.attempt_number, slot, token),
    )
    await get_storage().upload(ref, jpeg, "image/jpeg")
    row = CampaignVisualCandidate(
        attempt_id=attempt.id,
        slot=slot,
        kind=kind,
        storage_path=ref.to_path(),
        generation_job_id=job_id,
        variation_index=variation_index,
    )
    session.add(row)
    await session.flush()
    return row


async def _require_clean_reference(session: AsyncSession, campaign: Campaign) -> bytes:
    existing, _ = await load_creative_reference_bytes(session, campaign)
    if existing is not None:
        try:
            image = Image.open(io.BytesIO(existing))
            if min(image.size) >= MIN_REFERENCE_PX:
                return existing
        except Exception:
            pass
    crop, _ = await load_reference_bytes(session, campaign)
    original = await load_original_bytes(session, campaign)
    result = await prepare_clean_jpeg(original=original, crop_jpeg=crop)
    jpeg = assert_not_blocked(result)
    await store_clean_reference(session, campaign, jpeg)
    return jpeg


async def _current_attempt(
    session: AsyncSession, campaign: Campaign
) -> CampaignVisualAttempt | None:
    if campaign.current_visual_attempt_id is None:
        return None
    return await session.scalar(
        select(CampaignVisualAttempt).where(
            CampaignVisualAttempt.id == campaign.current_visual_attempt_id
        )
    )


def _as_jpeg(content: bytes) -> bytes:
    if content.startswith(b"\xff\xd8"):
        return content
    image = Image.open(io.BytesIO(content)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
