"""Creative-mode reference-image generation."""

from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import get_settings
from app.core.enums import FEED_SCENE_TYPES, STORY_SCENE_TYPES
from app.core.errors import generation_failed, invalid, not_found
from app.db.models import (
    Campaign,
    CampaignAsset,
    CampaignConcept,
    CampaignVisualAttempt,
    CampaignVisualCandidate,
    GenerationJob,
)
from app.providers.image import get_image_provider
from app.providers.image.base import (
    ImageApiError,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.creative_prompts import (
    build_repair_prompt,
    build_story_prompt,
)
from app.providers.vision import get_prompt_architect, get_visual_planner
from app.providers.vision.base import CandidateQuality, PlannerContext, QualityReport
from app.services.campaigns import cost as budgets
from app.services.campaigns import jobs as job_records
from app.services.campaigns import queries
from app.services.campaigns.creative_core import (
    architect_context_for,
    plan_slots,
    plan_validated_candidates,
    quality_to_dict,
)
from app.services.campaigns.product_composite import (
    composite_cutout_onto_scene,
    composite_looks_plausible,
)
from app.services.campaigns.product_media import (
    load_creative_reference_bytes,
    load_original_bytes,
    load_reference_bytes,
    store_clean_reference,
)
from app.services.campaigns.reference_prep import (
    assert_not_blocked,
    decide_strategy,
    extract_validated_cutout,
    prepare_clean_jpeg,
)
from app.services.campaigns.render_strategy import (
    REFERENCE_TRANSFORM,
    choose_creative_render_strategy,
)
from app.services.storage import get_storage, visual_candidate_key, visual_story_key
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)

ASPECT_4X5 = "4:5"
ASPECT_9X16 = "9:16"
MIN_REFERENCE_PX = 256


async def generate_candidates(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    *,
    source: str,
) -> None:
    recipe = campaign.visual_recipe_json or {}
    if not recipe.get("style_id") or not recipe.get("template_id"):
        raise invalid(messages.VISUAL_RECIPE_REQUIRED)

    await budgets.assert_can_start_attempt(session, campaign)
    analysis = _analysis_of(campaign)
    if decide_strategy(analysis) == "needs_user_action":
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)
    cleaned = await _require_clean_reference(session, campaign, analysis)
    original = await load_original_bytes(session, campaign)
    crop, _ = await load_reference_bytes(session, campaign)
    cutout_png = await extract_validated_cutout(crop or cleaned)
    concept = await _selected_concept(session, campaign)
    context = await _planner_context(session, campaign, concept, recipe)
    snapshot = campaign.planner_result_json or {}
    product_type = snapshot.get("product_type") if isinstance(snapshot, dict) else None
    choice = choose_creative_render_strategy(
        style_id=str(recipe.get("style_id") or ""),
        template_id=str(recipe.get("template_id") or ""),
        analysis=analysis,
        product_type=str(product_type) if product_type else None,
        cutout_png=cutout_png,
    )

    used = await budgets.attempt_count(session, campaign.id)
    attempt = CampaignVisualAttempt(
        campaign_id=campaign.id,
        attempt_number=used + 1,
        source=source if source in ("smart", "custom") else "custom",
        recipe_json=recipe,
        planner_json=(
            recipe.get("planner") if isinstance(recipe.get("planner"), dict) else {}
        ),
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
    if previous is not None and previous.status == "awaiting_selection":
        previous.status = "superseded"

    campaign.current_visual_attempt_id = attempt.id
    await session.flush()
    started_perf = time.perf_counter()

    run = await _run_architect(
        session,
        campaign,
        attempt,
        job.user_id,
        cleaned=cleaned,
        original=original,
        concept=concept,
        recipe=recipe,
        context=context,
        analysis=analysis,
        render_strategy=choice.strategy,
        render_strategy_reason=choice.reason,
    )
    slots = plan_slots(
        candidates=list(run.result.candidates),
        cleaned=cleaned,
        intended_strategy=run.effective_strategy,
    )
    payload = run.result.as_dict()
    payload["validation"] = run.validation
    payload["render_strategy"] = run.effective_strategy
    payload["render_strategy_reason"] = choice.reason
    payload["selector_strategy"] = choice.strategy
    payload["slot_strategies"] = [
        {
            "slot": item.candidate.slot,
            "strategy": item.used_strategy,
            "reason": item.fallback_reason,
        }
        for item in slots
    ]
    attempt.prompt_architect_json = payload
    await session.flush()

    frames, composite_failed = await _generate_slots(
        session,
        campaign,
        job,
        slots=slots,
        attempt_number=attempt.attempt_number,
        cutout_png=cutout_png,
    )
    stored: list[CampaignVisualCandidate] = []
    for index, frame in enumerate(frames):
        stored.append(
            await _store_candidate(
                session,
                campaign,
                attempt,
                slot=slots[index].candidate.slot if index < len(slots) else index + 1,
                jpeg=_as_jpeg(frame),
                job_id=job.id,
                kind="primary",
                variation_index=index,
            )
        )

    report = await _score_with_job(
        session, campaign, job.user_id, cleaned, tuple(frames), context
    )
    _apply_quality(stored, report)

    for row in stored:
        reason = composite_failed.get(row.slot)
        if reason:
            row.hard_failed = True
            row.hidden = True
            notes = (
                list(row.quality_json.get("reasons") or []) if row.quality_json else []
            )
            notes.append(reason)
            payload_q = dict(row.quality_json or {})
            payload_q["hard_failed"] = True
            payload_q["reasons"] = notes
            row.quality_json = payload_q

    failed = [row for row in stored if row.hard_failed]
    if failed and not attempt.auto_repair_used:
        failed_plan = next(
            (item for item in slots if item.candidate.slot == failed[0].slot),
            slots[0],
        )
        if (
            failed[0].slot not in composite_failed
            and failed_plan.used_strategy == REFERENCE_TRANSFORM
        ):
            await _repair_one(
                session,
                campaign,
                job,
                attempt,
                stored,
                failed[0],
                cleaned,
                failed_plan.prompt,
                context,
            )

    attempt.status = "awaiting_selection"
    payload = dict(attempt.prompt_architect_json or {})
    payload["wall_time_ms"] = int(round((time.perf_counter() - started_perf) * 1000))
    attempt.prompt_architect_json = payload
    campaign.updated_at = datetime.now(UTC)
    await session.flush()


async def select_winner(
    session: AsyncSession,
    campaign: Campaign,
    candidate_id: uuid.UUID,
    user_id: uuid.UUID | None,
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

    already = await budgets.count_outputs(
        session,
        campaign.id,
        attempt_number=attempt.attempt_number,
        role="story_adaptation",
    )
    story_path = None
    if already == 0:
        winner_bytes = await _download(candidate.storage_path)
        if winner_bytes is None:
            raise invalid(messages.GENERATION_FAILED)
        concept = await _selected_concept(session, campaign)
        recipe = attempt.recipe_json or campaign.visual_recipe_json or {}
        job = GenerationJob(
            campaign_id=campaign.id,
            user_id=user_id,
            job_type="image_generation",
            status="processing",
            started_at=datetime.now(UTC),
            input_json={},
        )
        session.add(job)
        await session.flush()
        result = await _generate_images(
            session,
            campaign,
            job,
            prompt=build_story_prompt(concept, campaign, recipe),
            aspect=ASPECT_9X16,
            role="story_adaptation",
            attempt_number=attempt.attempt_number,
            n=1,
            references=(winner_bytes,),
        )
        story_path = await _store_story(
            session, campaign, attempt, _as_jpeg(result.images()[0])
        )
        job_records.mark_image_succeeded(
            job,
            result.usage,
            provider=get_image_provider().name,
            output={"output_count": 1, "role": "story_adaptation"},
        )
    else:
        story_path = _existing_story(await queries.assets_of(session, campaign.id))

    attempt.selected_candidate_id = candidate.id
    attempt.status = "selected"
    campaign.status = "ready"
    campaign.updated_at = datetime.now(UTC)
    await _apply_winner(session, campaign, candidate.storage_path, story_path)
    await session.flush()


async def _repair_one(
    session: AsyncSession,
    campaign: Campaign,
    parent_job: GenerationJob,
    attempt: CampaignVisualAttempt,
    stored: list[CampaignVisualCandidate],
    failed: CampaignVisualCandidate,
    reference: bytes,
    compiled_prompt: str,
    context: PlannerContext,
) -> None:
    del stored
    already = await budgets.count_outputs(
        session,
        campaign.id,
        attempt_number=attempt.attempt_number,
        role="repair",
    )
    if already >= budgets.REPAIRS_PER_ATTEMPT:
        return
    await budgets.assert_auto_ceiling(session, campaign.id, attempt.attempt_number, 1)
    prompt = build_repair_prompt(compiled_prompt)
    result = await _generate_images(
        session,
        campaign,
        parent_job,
        prompt=prompt,
        aspect=ASPECT_4X5,
        role="repair",
        attempt_number=attempt.attempt_number,
        n=1,
        references=(reference,),
        nested=True,
    )
    frame = result.images()[0]
    repaired = await _store_candidate(
        session,
        campaign,
        attempt,
        slot=failed.slot,
        jpeg=_as_jpeg(frame),
        job_id=parent_job.id,
        kind="repair",
        variation_index=failed.variation_index,
    )
    report = await _score(reference, (frame,), context)
    _apply_quality([repaired], report)
    if not repaired.hard_failed:
        failed.hidden = True
    attempt.auto_repair_used = True
    await session.flush()


async def _generate_slots(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    *,
    slots,
    attempt_number: int,
    cutout_png: bytes | None,
) -> tuple[list[bytes], dict[int, str]]:
    n = len(slots)
    already = await budgets.count_outputs(
        session,
        campaign.id,
        attempt_number=attempt_number,
        role="candidate",
    )
    budgets.assert_role_budget("candidate", already, n)
    await budgets.assert_auto_ceiling(session, campaign.id, attempt_number, n)
    settings = get_settings()
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
    requests = [
        ImageRequest(
            prompt=item.prompt,
            aspect_ratio=ASPECT_4X5,
            resolution=settings.image_resolution,
            references=item.references,
            n=1,
        )
        for item in slots
    ]
    try:
        results = await asyncio.gather(
            *[get_image_provider().generate(request) for request in requests]
        )
    except ImageApiError:
        raise
    frames: list[bytes] = []
    usage: ImageUsage | None = None
    composite_failed: dict[int, str] = {}
    provider = get_image_provider()
    for slot, result in zip(slots, results, strict=True):
        raw = result.images()[0]
        usage = _merge_usage(usage, result.usage)
        jpeg = raw
        if slot.will_composite and cutout_png and slot.candidate.product_placement:
            pasted = composite_cutout_onto_scene(
                raw, cutout_png, slot.candidate.product_placement
            )
            if composite_looks_plausible(
                pasted, cutout_png, slot.candidate.product_placement
            ):
                jpeg = pasted
            else:
                reason = "composite could not plausibly integrate the cutout"
                composite_failed[slot.candidate.slot] = reason
                jpeg = pasted
        frames.append(jpeg)
    produced = len(frames)
    job.input_json = {
        **payload,
        "output_counts": {"candidate": produced},
        "output_count": produced,
        "n": produced,
    }
    job_records.apply_image_usage(job, usage, provider=provider.name)
    return frames, composite_failed


def _merge_usage(
    left: ImageUsage | None, right: ImageUsage | None
) -> ImageUsage | None:
    if left is None:
        return right
    if right is None:
        return left
    cost = None
    if left.cost_usd is not None or right.cost_usd is not None:
        cost = (left.cost_usd or Decimal("0")) + (right.cost_usd or Decimal("0"))
    return ImageUsage(
        latency_ms=left.latency_ms + right.latency_ms,
        cost_usd=cost,
        model=right.model or left.model,
        prompt_tokens=(left.prompt_tokens or 0) + (right.prompt_tokens or 0) or None,
        completion_tokens=(left.completion_tokens or 0) + (right.completion_tokens or 0)
        or None,
    )


async def _generate_images(
    session: AsyncSession,
    campaign: Campaign,
    job: GenerationJob,
    *,
    prompt: str,
    aspect: str,
    role: str,
    attempt_number: int,
    n: int,
    references: tuple[bytes, ...],
    nested: bool = False,
) -> ImageResult:
    already = await budgets.count_outputs(
        session,
        campaign.id,
        attempt_number=attempt_number,
        role=role,
    )
    budgets.assert_role_budget(role, already, n)
    await budgets.assert_auto_ceiling(session, campaign.id, attempt_number, n)
    settings = get_settings()
    payload = dict(job.input_json or {})
    payload["mode"] = "creative"
    payload["attempt_number"] = attempt_number
    payload["aspect"] = aspect
    if nested:
        counts = dict(payload.get("output_counts") or {})
        counts[role] = int(counts.get(role) or 0) + n
        payload["output_counts"] = counts
        payload["output_count"] = sum(
            int(v) for v in counts.values() if isinstance(v, int)
        )
        roles = list(payload.get("roles") or [])
        if role not in roles:
            roles.append(role)
        payload["roles"] = roles
    else:
        payload["role"] = role
        payload["n"] = n
        payload["output_count"] = n
        payload["output_counts"] = {role: n}
        payload["roles"] = [role]
    job.input_json = payload
    try:
        result = await get_image_provider().generate(
            ImageRequest(
                prompt=prompt,
                aspect_ratio=aspect,
                resolution=settings.image_resolution,
                references=references,
                n=n,
            )
        )
    except ImageApiError:
        raise
    produced = len(result.images())
    counts = dict((job.input_json or {}).get("output_counts") or {})
    if nested:
        counts[role] = int(counts.get(role) or 0) - n + produced
    else:
        counts[role] = produced
    job.input_json = {
        **payload,
        "output_counts": counts,
        "output_count": sum(int(v) for v in counts.values() if isinstance(v, int)),
        "n": produced if not nested else payload.get("n"),
    }
    if not nested:
        job_records.apply_image_usage(
            job, result.usage, provider=get_image_provider().name
        )
    return result


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


async def _store_story(
    session: AsyncSession,
    campaign: Campaign,
    attempt: CampaignVisualAttempt,
    jpeg: bytes,
) -> str:
    settings = get_settings()
    token = uuid.uuid4().hex[:12]
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=visual_story_key(campaign.id, attempt.attempt_number, token),
    )
    await get_storage().upload(ref, jpeg, "image/jpeg")
    await session.flush()
    return ref.to_path()


async def _apply_winner(
    session: AsyncSession,
    campaign: Campaign,
    feed_path: str,
    story_path: str | None,
) -> None:
    assets = await queries.assets_of(session, campaign.id)
    for asset in assets:
        spec = dict(asset.metadata_json or {})
        spec["visual_mode"] = "creative"
        spec["product_image_path"] = None
        spec["product_source"] = "generated"
        spec["failed"] = False
        if asset.asset_type in FEED_SCENE_TYPES:
            spec["scene_image_path"] = feed_path
        elif asset.asset_type in STORY_SCENE_TYPES:
            spec["scene_image_path"] = story_path or feed_path
        asset.metadata_json = spec
    await session.flush()


async def _require_clean_reference(
    session: AsyncSession, campaign: Campaign, analysis: dict
) -> bytes:
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
    result = await prepare_clean_jpeg(
        original=original, crop_jpeg=crop, analysis=analysis
    )
    jpeg = assert_not_blocked(result)
    await store_clean_reference(session, campaign, jpeg)
    return jpeg


def _analysis_of(campaign: Campaign) -> dict:
    snapshot = campaign.planner_result_json or {}
    raw = snapshot.get("reference_analysis")
    return dict(raw) if isinstance(raw, dict) else {}


async def _run_architect(
    session: AsyncSession,
    campaign: Campaign,
    attempt: CampaignVisualAttempt,
    user_id,
    *,
    cleaned: bytes,
    original: bytes | None,
    concept: CampaignConcept | None,
    recipe: dict,
    context: PlannerContext,
    analysis: dict,
    render_strategy: str = REFERENCE_TRANSFORM,
    render_strategy_reason: str = "",
):
    architect = get_prompt_architect()
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="prompt_architect",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "style_id": recipe.get("style_id"),
            "template_id": recipe.get("template_id"),
            "attempt_id": str(attempt.id),
            "render_strategy": render_strategy,
        },
    )
    session.add(job)
    await session.flush()
    try:
        run = await plan_validated_candidates(
            architect,
            cleaned=cleaned,
            original=original if original != cleaned else None,
            context=architect_context_for(
                campaign=campaign,
                concept=concept,
                recipe=recipe,
                planner_context=context,
                analysis=analysis,
                render_strategy=render_strategy,
                render_strategy_reason=render_strategy_reason,
            ),
            identity_constraints=list(recipe.get("identity_constraints") or []),
            template_id=str(recipe.get("template_id") or ""),
        )
    except Exception as error:
        job_records.mark_failed(job, error)
        raise
    if not run.validation.get("ok"):
        job.output_json = {"validation": run.validation}
        job_records.mark_failed(job, generation_failed())
        raise generation_failed()
    job.provider = architect.name
    job.model = architect.model
    if run.result.usage is not None:
        job_records.apply_llm_usage(job, run.result.usage)
    job_records.mark_succeeded(
        job,
        {
            "slots": [item.slot for item in run.result.candidates],
            "validation": run.validation,
            "render_strategy": run.effective_strategy,
        },
        consume_llm=False,
    )
    return run


async def _score_with_job(
    session: AsyncSession,
    campaign: Campaign,
    user_id,
    reference: bytes,
    frames: tuple[bytes, ...],
    context: PlannerContext,
) -> QualityReport:
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="visual_quality_check",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={"count": len(frames)},
    )
    session.add(job)
    await session.flush()
    try:
        report = await get_visual_planner().score_candidates(reference, frames, context)
    except Exception as error:
        logger.warning("visual quality scoring skipped: %s", error)
        job_records.mark_failed(job, error)
        return QualityReport(
            candidates=tuple(
                CandidateQuality(slot=index + 1, hard_failed=False)
                for index in range(len(frames))
            )
        )
    planner = get_visual_planner()
    job.provider = planner.name
    job.model = planner.model
    if report.usage is not None:
        job_records.apply_llm_usage(job, report.usage)
    job_records.mark_succeeded(
        job,
        {"slots": [item.slot for item in report.candidates]},
        consume_llm=False,
    )
    return report


async def _score(
    reference: bytes, frames: tuple[bytes, ...], context: PlannerContext
) -> QualityReport:
    try:
        return await get_visual_planner().score_candidates(reference, frames, context)
    except Exception as error:
        logger.warning("visual quality scoring skipped: %s", error)
        return QualityReport(
            candidates=tuple(
                CandidateQuality(slot=index + 1, hard_failed=False)
                for index in range(len(frames))
            )
        )


def _apply_quality(rows: list[CampaignVisualCandidate], report: QualityReport) -> None:
    by_slot = {item.slot: item for item in report.candidates}
    for index, row in enumerate(rows):
        item = by_slot.get(row.slot) or by_slot.get(index + 1)
        if item is None:
            continue
        row.quality_json = quality_to_dict(item)
        row.hard_failed = item.hard_failed
        row.hidden = item.hard_failed


async def _planner_context(
    session: AsyncSession,
    campaign: Campaign,
    concept: CampaignConcept | None,
    recipe: dict,
) -> PlannerContext:
    ctx = await queries.build_copy_context(session, campaign)
    return PlannerContext(
        product_name=ctx.product_name,
        description=ctx.description,
        brand_name=ctx.brand_name,
        price_text=ctx.price_text,
        audience=ctx.audience,
        objective=ctx.objective,
        visual_style=ctx.style,
        concept_title_fa=concept.title_fa if concept else "",
        concept_headline_fa=concept.headline_fa if concept else "",
        concept_visual_direction=concept.visual_direction if concept else "",
        recipe=recipe,
    )


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


def _existing_story(assets: list[CampaignAsset]) -> str | None:
    for asset in assets:
        if asset.asset_type == "story_final":
            spec = asset.metadata_json or {}
            path = spec.get("scene_image_path")
            if isinstance(path, str) and path:
                return path
    return None


async def _download(storage_path: str) -> bytes | None:
    from app.services.storage import parse

    ref = parse(storage_path)
    if ref is None:
        return None
    return await get_storage().download(ref)


def _as_jpeg(content: bytes) -> bytes:
    if content.startswith(b"\xff\xd8"):
        return content
    image = Image.open(io.BytesIO(content)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
