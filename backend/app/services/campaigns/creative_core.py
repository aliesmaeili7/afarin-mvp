"""DB-free creative generation shared by eval and production.

The Unified Creative Agent writes final_prompt and copy. Seedream receives
that prompt plus the cleaned reference. Campaign persistence stays in creative.py.
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
)
from app.providers.vision import get_creative_agent
from app.providers.vision.base import (
    CandidateQuality,
    CreativeAgentContext,
    CreativeAgentResult,
    QualityContext,
    QualityReport,
)
from app.providers.vision.creative_validate import (
    correction_user_block,
    merge_llm_usage,
    validate_creative_result,
)
from app.services.campaigns.reference_prep import prepare_clean_jpeg

logger = logging.getLogger(__name__)

ASPECT_4X5 = "4:5"

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
    prompt: str
    prompt_version: str
    candidates: list[GeneratedFrame] = field(default_factory=list)
    repairs: list[GeneratedFrame] = field(default_factory=list)
    quality: dict | None = None
    auto_repair_used: bool = False
    error: str | None = None
    candidate_request: dict | None = None
    creative_agent: dict | None = None
    cleaned_jpeg: bytes | None = None
    prompts: list[str] = field(default_factory=list)
    llm_calls: list[dict] = field(default_factory=list)
    image_requests: list[dict] = field(default_factory=list)
    requested_image_count: int = 1
    successful_image_count: int = 0


@dataclass(frozen=True, slots=True)
class AgentRun:
    result: CreativeAgentResult
    validation: dict
    retry_used: bool
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
    agent: Any,
    reference: bytes,
    frames: tuple[bytes, ...],
    context: QualityContext,
) -> QualityReport:
    try:
        return await agent.score_candidates(reference, frames, context)
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


async def plan_validated_campaign(
    agent: Any,
    *,
    cleaned: bytes,
    context: CreativeAgentContext,
) -> AgentRun:
    planned = await agent.create_campaign(cleaned, context)
    traces = [planned.llm_trace] if planned.llm_trace is not None else []
    validation = validate_creative_result(
        planned, requested_image_count=context.requested_image_count
    )
    retry_used = False
    if not validation.ok:
        retry_used = True
        retry = await agent.create_campaign(
            cleaned,
            context,
            correction=correction_user_block(validation.errors),
        )
        if retry.llm_trace is not None:
            traces.append(retry.llm_trace)
        planned = replace(
            retry,
            usage=merge_llm_usage(planned.usage, retry.usage),
        )
        validation = validate_creative_result(
            planned, requested_image_count=context.requested_image_count
        )
    return AgentRun(
        result=planned,
        validation=validation.as_dict(retry_used=retry_used),
        retry_used=retry_used,
        traces=tuple(traces),
    )


def quality_context_for(context: CreativeAgentContext) -> QualityContext:
    constraints: list[str] = []
    return QualityContext(
        product_name=context.product_name,
        template_id=context.template_id,
        identity_constraints=tuple(constraints),
    )


async def generate_recipe_set(
    *,
    context: CreativeAgentContext,
    reference: bytes,
    provider: ImageProvider,
    agent: Any | None = None,
    quality_check: bool = False,
    repair: RepairMode = "none",
    resolution: str | None = None,
    timestamp: str = "",
    original: bytes | None = None,
    on_stage=None,
) -> RecipeSetResult:
    settings = get_settings()
    res = resolution or settings.image_resolution
    prep = await prepare_clean_jpeg(original=original, crop_jpeg=reference)
    out = RecipeSetResult(
        prompt="",
        prompt_version=CREATIVE_PROMPT_VERSION,
        requested_image_count=context.requested_image_count,
    )
    if prep.blocked or prep.jpeg is None:
        out.error = "; ".join(prep.reasons) or "needs_user_action"
        return out
    cleaned = prep.jpeg
    out.cleaned_jpeg = cleaned
    if context.requested_image_count <= 0:
        return out

    planner = agent or get_creative_agent()
    run = await plan_validated_campaign(planner, cleaned=cleaned, context=context)
    for trace in run.traces:
        _append_trace(out, trace)
    payload = run.result.as_dict()
    payload["validation"] = run.validation
    if run.result.usage is not None:
        payload["usage"] = {
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
    out.creative_agent = payload
    if not run.validation.get("ok"):
        out.error = "; ".join(run.validation.get("errors") or []) or (
            "creative_agent_validation_failed"
        )
        return out

    concepts = list(run.result.images)
    out.prompts = [item.final_prompt for item in concepts]
    out.prompt = out.prompts[0] if out.prompts else ""

    if on_stage is not None:
        await on_stage("visual")

    requests = [
        ImageRequest(
            prompt=item.final_prompt,
            aspect_ratio=ASPECT_4X5,
            resolution=res,
            references=(cleaned,),
            n=1,
        )
        for item in concepts
    ]
    if requests:
        out.candidate_request = request_summary(
            requests[0], provider=provider.name, model=provider.model
        )
    results = await asyncio.gather(*[provider.generate(req) for req in requests])
    frames = [result.images()[0] for result in results]
    if on_stage is not None:
        await on_stage("finalizing")

    report: QualityReport | None = None
    qctx = quality_context_for(context)
    if quality_check:
        report = await score_frames(planner, cleaned, tuple(frames), qctx)
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
    for index, (concept, request, result, jpeg) in enumerate(
        zip(concepts, requests, results, frames, strict=True)
    ):
        slot = index + 1
        item = by_slot.get(slot)
        quality = quality_to_dict(item) if item else None
        hard = bool(item.hard_failed) if item else False
        out.candidates.append(
            _frame(
                slot=slot,
                kind="primary",
                role="candidate",
                jpeg=jpeg,
                prompt=concept.final_prompt,
                variation=index,
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
    out.successful_image_count = sum(1 for row in out.candidates if not row.hidden)

    failed = next((row for row in out.candidates if row.hard_failed), None)
    if repair == "production" and failed is not None and not out.auto_repair_used:
        repaired = await _repair_one(
            failed=failed,
            reference=cleaned,
            provider=provider,
            agent=planner,
            quality_check=quality_check,
            quality_context=qctx,
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
            out.successful_image_count = sum(
                1 for row in out.candidates if not row.hidden
            ) + (0 if repaired.hidden else 0)
            if not repaired.hidden:
                out.successful_image_count = sum(
                    1 for row in (*out.candidates, repaired) if not row.hidden
                )
    return out


async def _repair_one(
    *,
    failed: GeneratedFrame,
    reference: bytes,
    provider: ImageProvider,
    agent: Any | None,
    quality_check: bool,
    quality_context: QualityContext,
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
    if quality_check and agent is not None:
        report = await score_frames(agent, reference, (raw,), quality_context)
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
        variation=failed.slot + 10,
        quality=quality,
        hard_failed=hard,
        hidden=hard,
        repaired=False,
        result=result,
        request=request,
        provider=provider,
        timestamp=timestamp,
    )


def add_costs(*values: str | None) -> Decimal:
    total = Decimal("0")
    found = False
    for raw in values:
        if raw is None:
            continue
        total += Decimal(raw)
        found = True
    return total if found else Decimal("0")
