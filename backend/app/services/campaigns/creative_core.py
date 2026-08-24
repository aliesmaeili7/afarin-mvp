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
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from PIL import Image

from app.core.config import get_settings
from app.content.visual_catalog import selected_semantics
from app.providers.image.base import (
    ImageProvider,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.creative_prompts import (
    CREATIVE_PROMPT_VERSION,
    compile_architect_result,
    build_repair_prompt,
    build_story_prompt,
)
from app.providers.vision import get_prompt_architect
from app.providers.vision.base import (
    ArchitectContext,
    CandidateQuality,
    PlannerContext,
    QualityReport,
)
from app.services.campaigns.master_crop import MASTER_NOTE, central_4x5_crop
from app.services.campaigns.reference_prep import prepare_clean_jpeg

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

    context = architect_context_for(
        campaign=campaign,
        concept=concept,
        recipe=recipe,
        planner_context=planner_context,
        analysis=analysis,
    )
    planner_impl = architect or get_prompt_architect()
    planned = await planner_impl.plan_candidates(
        cleaned, context, original=original if original != cleaned else None
    )
    _append_trace(out, planned.llm_trace)
    compiled = compile_architect_result(
        planned,
        identity_constraints=list(recipe.get("identity_constraints") or []),
        text_safe_area=str(recipe.get("text_safe_area") or "bottom"),
    )
    out.architect = compiled.as_dict()
    if compiled.usage is not None:
        out.architect["usage"] = {
            "latency_ms": compiled.usage.latency_ms,
            "cost_usd": (
                str(compiled.usage.cost_usd)
                if compiled.usage.cost_usd is not None
                else None
            ),
            "model": compiled.usage.model,
            "prompt_tokens": compiled.usage.prompt_tokens,
            "completion_tokens": compiled.usage.completion_tokens,
        }
    chosen = list(compiled.candidates[:n])
    out.prompts = [item.compiled_prompt for item in chosen]
    out.prompt = out.prompts[0] if out.prompts else ""

    requests = [
        ImageRequest(
            prompt=item.compiled_prompt,
            aspect_ratio=ASPECT_4X5,
            resolution=res,
            references=(cleaned,),
            n=1,
        )
        for item in chosen
    ]
    if requests:
        out.candidate_request = request_summary(
            requests[0], provider=provider.name, model=provider.model
        )
    results = await asyncio.gather(*[provider.generate(req) for req in requests])
    frames = [result.images()[0] for result in results]
    report: QualityReport | None = None
    if quality_check and planner is not None:
        report = await score_frames(
            planner, cleaned, tuple(frames), planner_context
        )
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
    for index, (raw, request, result, spec) in enumerate(
        zip(frames, requests, results, chosen, strict=True)
    ):
        item = by_slot.get(spec.slot) or by_slot.get(index + 1)
        quality = quality_to_dict(item) if item else None
        hard = bool(item.hard_failed) if item else False
        out.candidates.append(
            _frame(
                slot=spec.slot,
                kind="primary",
                role="candidate",
                jpeg=raw,
                prompt=spec.compiled_prompt,
                variation=spec.slot - 1,
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
