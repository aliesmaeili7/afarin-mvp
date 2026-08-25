"""DB-free creative generation shared by eval.

Campaign persistence, budgets, and wizard status stay in creative.py.
Prompts, provider calls, QC, and the one-repair rule live here so eval and
production send the same strings to the image model.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any, Literal

from PIL import Image

from app.content.visual_catalog import selected_semantics
from app.core.config import get_settings
from app.providers.image.base import (
    ImageProvider,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.creative_prompts import (
    CREATIVE_PROMPT_VERSION,
    build_repair_prompt,
    build_story_prompt,
)
from app.providers.vision import get_prompt_architect
from app.providers.vision.architect_validate import (
    correction_user_block,
    merge_llm_usage,
    placement_unusable,
    validate_architect_result,
)
from app.providers.vision.base import (
    ArchitectCandidate,
    ArchitectContext,
    CandidateQuality,
    PlannerContext,
    PromptArchitectResult,
    QualityReport,
)
from app.services.campaigns.master_crop import MASTER_NOTE, central_4x5_crop
from app.services.campaigns.product_composite import (
    composite_cutout_onto_scene,
    composite_looks_plausible,
)
from app.services.campaigns.reference_prep import (
    extract_validated_cutout,
    prepare_clean_jpeg,
)
from app.services.campaigns.render_strategy import (
    PRESERVED_PRODUCT_COMPOSITE,
    REFERENCE_TRANSFORM,
    choose_creative_render_strategy,
)

logger = logging.getLogger(__name__)

ASPECT_4X5 = "4:5"
ASPECT_9X16 = "9:16"

RepairMode = Literal["none", "production"]


@dataclass
class GeneratedFrame:
    slot: int
    kind: str
    role: str
    jpeg: bytes
    prompt: str
    variation: int
    quality: dict | None
    hard_failed: bool
    hidden: bool
    repaired: bool
    usage: dict
    width: int
    height: int
    request_summary: dict
    model: str | None
    provider: str
    latency_ms: int
    cost_usd: str | None
    timestamp: str


@dataclass
class RecipeSetResult:
    recipe: dict
    prompt: str
    prompt_version: str
    candidates: list[GeneratedFrame] = field(default_factory=list)
    repairs: list[GeneratedFrame] = field(default_factory=list)
    story: GeneratedFrame | None = None
    master: GeneratedFrame | None = None
    master_crop_jpeg: bytes | None = None
    quality: dict | None = None
    auto_repair_used: bool = False
    error: str | None = None
    candidate_request: dict | None = None
    architect: dict | None = None
    cleaned_jpeg: bytes | None = None
    prompts: list[str] = field(default_factory=list)
    compatibility: str | None = None
    llm_calls: list[dict] = field(default_factory=list)
    image_requests: list[dict] = field(default_factory=list)
    render_strategy: str | None = None
    render_strategy_reason: str | None = None
    cutout_png: bytes | None = None
    scene_jpegs: dict[int, bytes] = field(default_factory=dict)
    slot_strategies: list[dict] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SlotPlan:
    candidate: ArchitectCandidate
    prompt: str
    references: tuple[bytes, ...]
    will_composite: bool
    used_strategy: str
    fallback_reason: str = ""


@dataclass(frozen=True, slots=True)
class ArchitectRun:
    result: PromptArchitectResult
    validation: dict
    effective_strategy: str
    retry_used: bool
    switched_to_transform: bool = False
    traces: tuple[Any, ...] = ()


def as_jpeg(content: bytes) -> bytes:
    if content.startswith(b"\xff\xd8"):
        return content
    image = Image.open(io.BytesIO(content)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def usage_dict(usage: ImageUsage | None) -> dict:
    if usage is None:
        return {"latency_ms": 0, "cost_usd": None, "model": None}
    cost = usage.cost_usd
    return {
        "latency_ms": usage.latency_ms,
        "cost_usd": str(cost) if cost is not None else None,
        "model": usage.model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    }


def request_summary(
    request: ImageRequest,
    *,
    provider: str,
    model: str | None,
) -> dict:
    return {
        "provider": provider,
        "model": model,
        "aspect_ratio": request.aspect_ratio,
        "resolution": request.resolution,
        "n": request.n,
        "seed": request.seed,
        "seed_supported": False,
        "output_format": request.output_format,
        "prompt_chars": len(request.prompt),
        "references": [
            {
                "sha256": hashlib.sha256(item).hexdigest(),
                "bytes": len(item),
            }
            for item in request.references
        ],
    }


def quality_to_dict(item: CandidateQuality) -> dict:
    return {
        "slot": item.slot,
        "hard_failed": item.hard_failed,
        "reasons": list(item.reasons),
        "identity_recognizable": item.identity_recognizable,
        "no_random_text_or_logos": item.no_random_text_or_logos,
        "no_severe_artifacts": item.no_severe_artifacts,
        "no_unwanted_duplicates": item.no_unwanted_duplicates,
        "ad_composition": item.ad_composition,
        "text_safe_space": item.text_safe_space,
        "identity_quality": item.identity_quality,
        "style_adherence": item.style_adherence,
        "template_adherence": item.template_adherence,
        "composition_quality": item.composition_quality,
        "visual_attractiveness": item.visual_attractiveness,
        "commercial_usefulness": item.commercial_usefulness,
        "text_safe_space_quality": item.text_safe_space_quality,
    }


async def score_frames(
    planner: Any,
    reference: bytes,
    frames: tuple[bytes, ...],
    context: PlannerContext,
) -> QualityReport:
    try:
        return await planner.score_candidates(reference, frames, context)
    except Exception as error:
        logger.warning("visual quality scoring skipped: %s", error)
        return QualityReport(
            candidates=tuple(
                CandidateQuality(slot=index + 1, hard_failed=False)
                for index in range(len(frames))
            )
        )


def _dimensions(jpeg: bytes) -> tuple[int, int]:
    image = Image.open(io.BytesIO(jpeg))
    return image.size


def _frame(
    *,
    slot: int,
    kind: str,
    role: str,
    jpeg: bytes,
    prompt: str,
    variation: int,
    quality: dict | None,
    hard_failed: bool,
    hidden: bool,
    repaired: bool,
    result: ImageResult,
    request: ImageRequest,
    provider: ImageProvider,
    timestamp: str,
) -> GeneratedFrame:
    jpeg = as_jpeg(jpeg)
    width, height = _dimensions(jpeg)
    usage = usage_dict(result.usage)
    return GeneratedFrame(
        slot=slot,
        kind=kind,
        role=role,
        jpeg=jpeg,
        prompt=prompt,
        variation=variation,
        quality=quality,
        hard_failed=hard_failed,
        hidden=hidden,
        repaired=repaired,
        usage=usage,
        width=width,
        height=height,
        request_summary=request_summary(
            request, provider=provider.name, model=provider.model
        ),
        model=provider.model,
        provider=provider.name,
        latency_ms=int(usage.get("latency_ms") or 0),
        cost_usd=usage.get("cost_usd"),
        timestamp=timestamp,
    )


def _image_call(frame: GeneratedFrame) -> dict:
    names = {
        "primary": f"candidate-{frame.slot}.jpg",
        "repair": f"repair-{frame.slot}.jpg",
        "story": "story.jpg",
        "master": "master-9x16.jpg",
    }
    return {
        "kind": frame.kind,
        "role": frame.role,
        "slot": frame.slot,
        "file": names.get(frame.kind, f"{frame.kind}-{frame.slot}.jpg"),
        "prompt": frame.prompt,
        "provider": frame.provider,
        "model": frame.model,
        "aspect_ratio": frame.request_summary.get("aspect_ratio"),
        "resolution": frame.request_summary.get("resolution"),
        "n": frame.request_summary.get("n"),
        "references": frame.request_summary.get("references") or [],
    }


def _append_trace(out: RecipeSetResult, trace: Any) -> None:
    if trace is None:
        return
    payload = trace.as_dict() if hasattr(trace, "as_dict") else None
    if payload:
        out.llm_calls.append(payload)


def architect_context_for(
    *,
    campaign: Any,
    concept: Any | None,
    recipe: dict,
    planner_context: PlannerContext,
    analysis: dict,
    render_strategy: str = REFERENCE_TRANSFORM,
    render_strategy_reason: str = "",
) -> ArchitectContext:
    style_id = str(recipe.get("style_id") or "")
    template_id = str(recipe.get("template_id") or "")
    semantics = {}
    if style_id and template_id:
        try:
            semantics = selected_semantics(style_id, template_id)
        except KeyError:
            semantics = {}
    return ArchitectContext(
        product_name=planner_context.product_name,
        description=planner_context.description,
        brand_name=planner_context.brand_name,
        audience=planner_context.audience,
        objective=planner_context.objective,
        visual_style=getattr(campaign, "visual_style", None)
        or planner_context.visual_style,
        recipe=recipe,
        reference_analysis=analysis,
        identity_constraints=tuple(recipe.get("identity_constraints") or ()),
        concept_title_fa=getattr(concept, "title_fa", "") or "",
        concept_visual_direction=getattr(concept, "visual_direction", "")
        or planner_context.concept_visual_direction,
        compatibility=str(
            recipe.get("compatibility") or semantics.get("compatibility") or "allowed"
        ),
        style_semantics=dict(semantics.get("style") or {}),
        template_semantics=dict(semantics.get("template") or {}),
        text_safe_area=str(recipe.get("text_safe_area") or "bottom"),
        render_strategy=render_strategy,
        render_strategy_reason=render_strategy_reason,
    )


def plan_slots(
    *,
    candidates: list[ArchitectCandidate],
    cleaned: bytes,
    intended_strategy: str,
) -> list[SlotPlan]:
    slots: list[SlotPlan] = []
    for item in candidates:
        prompt = item.final_prompt
        if intended_strategy == PRESERVED_PRODUCT_COMPOSITE:
            slots.append(
                SlotPlan(
                    candidate=item,
                    prompt=prompt,
                    references=(),
                    will_composite=True,
                    used_strategy=PRESERVED_PRODUCT_COMPOSITE,
                )
            )
            continue
        slots.append(
            SlotPlan(
                candidate=item,
                prompt=prompt,
                references=(cleaned,),
                will_composite=False,
                used_strategy=REFERENCE_TRANSFORM,
            )
        )
    return slots


async def plan_validated_candidates(
    architect: Any,
    *,
    cleaned: bytes,
    original: bytes | None,
    context: ArchitectContext,
    identity_constraints: list[str] | tuple[str, ...],
    template_id: str,
) -> ArchitectRun:
    planned = await architect.plan_candidates(
        cleaned, context, original=original
    )
    traces = [planned.llm_trace] if planned.llm_trace is not None else []
    validation = validate_architect_result(
        planned,
        render_strategy=context.render_strategy,
        identity_constraints=identity_constraints,
        template_id=template_id,
    )
    retry_used = False
    switched = False
    effective = context.render_strategy
    if not validation.ok:
        retry_used = True
        retry_context = context
        if (
            context.render_strategy == PRESERVED_PRODUCT_COMPOSITE
            and placement_unusable(validation)
        ):
            switched = True
            effective = REFERENCE_TRANSFORM
            retry_context = replace(context, render_strategy=REFERENCE_TRANSFORM)
        retry = await architect.plan_candidates(
            cleaned,
            retry_context,
            original=original,
            correction=correction_user_block(
                validation.errors, switch_to_transform=switched
            ),
        )
        if retry.llm_trace is not None:
            traces.append(retry.llm_trace)
        planned = PromptArchitectResult(
            reference_summary=retry.reference_summary,
            candidates=retry.candidates,
            usage=merge_llm_usage(planned.usage, retry.usage),
            llm_trace=retry.llm_trace,
        )
        validation = validate_architect_result(
            planned,
            render_strategy=effective,
            identity_constraints=identity_constraints,
            template_id=template_id,
        )
    payload = validation.as_dict(
        retry_used=retry_used, switched_to_transform=switched
    )
    return ArchitectRun(
        result=PromptArchitectResult(
            reference_summary=planned.reference_summary,
            candidates=planned.candidates,
            usage=planned.usage,
            llm_trace=traces[-1] if traces else planned.llm_trace,
        ),
        validation=payload,
        effective_strategy=effective,
        retry_used=retry_used,
        switched_to_transform=switched,
        traces=tuple(traces),
    )


async def generate_recipe_set(
    *,
    recipe: dict,
    reference: bytes,
    campaign: Any,
    concept: Any | None,
    planner_context: PlannerContext,
    provider: ImageProvider,
    planner: Any | None,
    n: int,
    variation: int = 0,
    quality_check: bool = False,
    repair: RepairMode = "none",
    story: bool = False,
    master_crop: bool = False,
    resolution: str | None = None,
    timestamp: str = "",
    original: bytes | None = None,
    analysis: dict | None = None,
    architect: Any | None = None,
    product_type: str | None = None,
    category: str | None = None,
) -> RecipeSetResult:
    """Generate candidates for one style/template using production prompts."""
    del variation
    settings = get_settings()
    res = resolution or settings.image_resolution
    analysis = analysis or {}
    if not analysis and isinstance(recipe.get("planner"), dict):
        analysis = dict(recipe["planner"].get("reference_analysis") or {})
    prep = await prepare_clean_jpeg(
        original=original, crop_jpeg=reference, analysis=analysis
    )
    out = RecipeSetResult(
        recipe=recipe,
        prompt="",
        prompt_version=CREATIVE_PROMPT_VERSION,
        compatibility=str(recipe.get("compatibility") or ""),
    )
    if prep.blocked or prep.jpeg is None:
        out.error = "; ".join(prep.reasons) or "needs_user_action"
        return out
    cleaned = prep.jpeg
    out.cleaned_jpeg = cleaned
    if n <= 0:
        return out

    cutout_png = await extract_validated_cutout(reference)
    out.cutout_png = cutout_png
    kind = product_type or analysis.get("product_type")
    choice = choose_creative_render_strategy(
        style_id=str(recipe.get("style_id") or ""),
        template_id=str(recipe.get("template_id") or ""),
        analysis=analysis,
        product_type=kind if isinstance(kind, str) else None,
        category=category,
        cutout_png=cutout_png,
    )
    out.render_strategy = choice.strategy
    out.render_strategy_reason = choice.reason

    context = architect_context_for(
        campaign=campaign,
        concept=concept,
        recipe=recipe,
        planner_context=planner_context,
        analysis=analysis,
        render_strategy=choice.strategy,
        render_strategy_reason=choice.reason,
    )
    planner_impl = architect or get_prompt_architect()
    run = await plan_validated_candidates(
        planner_impl,
        cleaned=cleaned,
        original=original if original != cleaned else None,
        context=context,
        identity_constraints=list(recipe.get("identity_constraints") or []),
        template_id=str(recipe.get("template_id") or ""),
    )
    for trace in run.traces:
        _append_trace(out, trace)
    out.architect = run.result.as_dict()
    out.architect["validation"] = run.validation
    out.architect["render_strategy"] = run.effective_strategy
    out.architect["render_strategy_reason"] = choice.reason
    out.architect["selector_strategy"] = choice.strategy
    if run.result.usage is not None:
        out.architect["usage"] = {
            "latency_ms": run.result.usage.latency_ms,
            "cost_usd": (
                str(run.result.usage.cost_usd)
                if run.result.usage.cost_usd is not None
                else None
            ),
            "model": run.result.usage.model,
            "prompt_tokens": run.result.usage.prompt_tokens,
            "completion_tokens": run.result.usage.completion_tokens,
        }
    out.render_strategy = run.effective_strategy
    out.render_strategy_reason = choice.reason
    if not run.validation.get("ok"):
        out.error = "; ".join(run.validation.get("errors") or []) or (
            "architect_validation_failed"
        )
        return out
    chosen = list(run.result.candidates[:n])
    slots = plan_slots(
        candidates=chosen,
        cleaned=cleaned,
        intended_strategy=run.effective_strategy,
    )
    out.prompts = [item.prompt for item in slots]
    out.prompt = out.prompts[0] if out.prompts else ""
    out.slot_strategies = [
        {
            "slot": item.candidate.slot,
            "strategy": item.used_strategy,
            "reason": item.fallback_reason,
        }
        for item in slots
    ]

    requests = [
        ImageRequest(
            prompt=item.prompt,
            aspect_ratio=ASPECT_4X5,
            resolution=res,
            references=item.references,
            n=1,
        )
        for item in slots
    ]
    if requests:
        out.candidate_request = request_summary(
            requests[0], provider=provider.name, model=provider.model
        )
    results = await asyncio.gather(*[provider.generate(req) for req in requests])
    produced: list[tuple[SlotPlan, ImageRequest, ImageResult, bytes]] = []
    composite_failed: dict[int, str] = {}
    for slot, request, result in zip(slots, requests, results, strict=True):
        raw = result.images()[0]
        jpeg = raw
        used = slot
        used_request = request
        used_result = result
        if slot.will_composite and cutout_png and slot.candidate.product_placement:
            out.scene_jpegs[slot.candidate.slot] = as_jpeg(raw)
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
                used = SlotPlan(
                    candidate=slot.candidate,
                    prompt=slot.prompt,
                    references=(),
                    will_composite=True,
                    used_strategy=PRESERVED_PRODUCT_COMPOSITE,
                    fallback_reason=reason,
                )
        produced.append((used, used_request, used_result, jpeg))
    frames = [jpeg for _used, _req, _res, jpeg in produced]
    out.prompts = [item.prompt for item, *_rest in produced]
    out.prompt = out.prompts[0] if out.prompts else ""
    out.slot_strategies = [
        {
            "slot": item.candidate.slot,
            "strategy": item.used_strategy,
            "reason": item.fallback_reason,
        }
        for item, *_rest in produced
    ]

    report: QualityReport | None = None
    if quality_check and planner is not None:
        report = await score_frames(planner, cleaned, tuple(frames), planner_context)
        out.quality = {
            "candidates": [quality_to_dict(item) for item in report.candidates]
        }
        _append_trace(out, report.llm_trace)
        if report.usage is not None:
            out.quality["usage"] = {
                "latency_ms": report.usage.latency_ms,
                "cost_usd": (
                    str(report.usage.cost_usd)
                    if report.usage.cost_usd is not None
                    else None
                ),
                "model": report.usage.model,
            }

    by_slot = {item.slot: item for item in report.candidates} if report else {}
    for index, (spec, request, result, jpeg) in enumerate(produced):
        item = by_slot.get(spec.candidate.slot) or by_slot.get(index + 1)
        quality = quality_to_dict(item) if item else None
        hard = bool(item.hard_failed) if item else False
        composite_reason = composite_failed.get(spec.candidate.slot)
        if composite_reason:
            hard = True
            quality = dict(quality or {})
            quality["hard_failed"] = True
            reasons = list(quality.get("reasons") or [])
            reasons.append(composite_reason)
            quality["reasons"] = reasons
        out.candidates.append(
            _frame(
                slot=spec.candidate.slot,
                kind="primary",
                role="candidate",
                jpeg=jpeg,
                prompt=spec.prompt,
                variation=spec.candidate.slot - 1,
                quality=quality,
                hard_failed=hard,
                hidden=hard,
                repaired=False,
                result=result,
                request=request,
                provider=provider,
                timestamp=timestamp,
            )
        )

    out.image_requests.extend(_image_call(frame) for frame in out.candidates)

    failed = next((row for row in out.candidates if row.hard_failed), None)
    if repair == "production" and failed is not None and not out.auto_repair_used:
        failed_spec = next(
            (item for item, *_rest in produced if item.candidate.slot == failed.slot),
            None,
        )
        if (
            failed_spec is None
            or failed_spec.used_strategy == REFERENCE_TRANSFORM
        ):
            repaired = await _repair_one(
                failed=failed,
                recipe=recipe,
                reference=cleaned,
                campaign=campaign,
                concept=concept,
                planner_context=planner_context,
                provider=provider,
                planner=planner,
                variation=failed.slot,
                quality_check=quality_check,
                resolution=res,
                timestamp=timestamp,
                traces=out.llm_calls,
            )
            out.repairs.append(repaired)
            out.image_requests.append(_image_call(repaired))
            out.auto_repair_used = True
            if not repaired.hard_failed:
                failed.hidden = True
                failed.repaired = True

    winner = next((row for row in out.candidates if not row.hidden), None)
    if winner is None and out.candidates:
        winner = out.candidates[0]
    if (story or master_crop) and winner is not None:
        out.story = await _story(
            winner=winner,
            recipe=recipe,
            campaign=campaign,
            concept=concept,
            provider=provider,
            resolution=res,
            timestamp=timestamp,
        )
        out.image_requests.append(_image_call(out.story))
    if master_crop:
        out.master, out.master_crop_jpeg = await _master(
            prompt=out.prompt,
            reference=cleaned,
            provider=provider,
            resolution=res,
            timestamp=timestamp,
        )
        out.image_requests.append(_image_call(out.master))
    return out


async def _repair_one(
    *,
    failed: GeneratedFrame,
    recipe: dict,
    reference: bytes,
    campaign: Any,
    concept: Any | None,
    planner_context: PlannerContext,
    provider: ImageProvider,
    planner: Any | None,
    variation: int,
    quality_check: bool,
    resolution: str,
    timestamp: str,
    traces: list[dict] | None = None,
) -> GeneratedFrame:
    prompt = build_repair_prompt(failed.prompt)
    request = ImageRequest(
        prompt=prompt,
        aspect_ratio=ASPECT_4X5,
        resolution=resolution,
        references=(reference,),
        n=1,
    )
    result = await provider.generate(request)
    raw = result.images()[0]
    item: CandidateQuality | None = None
    if quality_check and planner is not None:
        report = await score_frames(planner, reference, (raw,), planner_context)
        item = report.candidates[0] if report.candidates else None
        if traces is not None and report.llm_trace is not None:
            traces.append(report.llm_trace.as_dict())
    quality = quality_to_dict(item) if item else None
    hard = bool(item.hard_failed) if item else False
    return _frame(
        slot=failed.slot,
        kind="repair",
        role="repair",
        jpeg=raw,
        prompt=prompt,
        variation=variation + 10,
        quality=quality,
        hard_failed=hard,
        hidden=hard,
        repaired=False,
        result=result,
        request=request,
        provider=provider,
        timestamp=timestamp,
    )


async def _story(
    *,
    winner: GeneratedFrame,
    recipe: dict,
    campaign: Any,
    concept: Any | None,
    provider: ImageProvider,
    resolution: str,
    timestamp: str,
) -> GeneratedFrame:
    prompt = build_story_prompt(concept, campaign, recipe)
    request = ImageRequest(
        prompt=prompt,
        aspect_ratio=ASPECT_9X16,
        resolution=resolution,
        references=(winner.jpeg,),
        n=1,
    )
    result = await provider.generate(request)
    return _frame(
        slot=winner.slot,
        kind="story",
        role="story_adaptation",
        jpeg=result.images()[0],
        prompt=prompt,
        variation=0,
        quality=None,
        hard_failed=False,
        hidden=False,
        repaired=False,
        result=result,
        request=request,
        provider=provider,
        timestamp=timestamp,
    )


async def _master(
    *,
    prompt: str,
    reference: bytes,
    provider: ImageProvider,
    resolution: str,
    timestamp: str,
) -> tuple[GeneratedFrame, bytes]:
    master_prompt = f"{prompt}, {MASTER_NOTE}"
    request = ImageRequest(
        prompt=master_prompt,
        aspect_ratio=ASPECT_9X16,
        resolution=resolution,
        references=(reference,),
        n=1,
    )
    result = await provider.generate(request)
    jpeg = as_jpeg(result.images()[0])
    image = Image.open(io.BytesIO(jpeg)).convert("RGB")
    crop = central_4x5_crop(image)
    buffer = io.BytesIO()
    crop.save(buffer, format="JPEG", quality=90)
    frame = _frame(
        slot=1,
        kind="master",
        role="master",
        jpeg=jpeg,
        prompt=master_prompt,
        variation=0,
        quality=None,
        hard_failed=False,
        hidden=False,
        repaired=False,
        result=result,
        request=request,
        provider=provider,
        timestamp=timestamp,
    )
    return frame, buffer.getvalue()


def add_costs(*values: str | None) -> Decimal:
    total = Decimal("0")
    found = False
    for raw in values:
        if raw is None:
            continue
        total += Decimal(raw)
        found = True
    return total if found else Decimal("0")
