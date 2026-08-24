from __future__ import annotations

import base64
import io
import logging
from typing import Any

from PIL import Image
from pydantic import ValidationError

from app.content.visual_catalog import compatibility, style_ids, template_ids
from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter.client import LlmClient, parse_json_object
from app.providers.llm.openrouter.schemas import strict_schema
from app.providers.vision.base import (
    ArchitectCandidate,
    ArchitectComposition,
    ArchitectContext,
    CampaignDirection,
    CandidateQuality,
    CropBox,
    IdentityFeature,
    InputQuality,
    LlmCallTrace,
    PlannerContext,
    PlannerResult,
    PromptArchitectResult,
    QualityReport,
    ReferenceAnalysis,
    llm_image_ref,
    llm_usage_dict,
)
from app.providers.vision.prompts import (
    ARCHITECT_SYSTEM,
    QUALITY_SYSTEM,
    architect_user_prompt,
    plan_user_prompt,
    planner_system,
    quality_user_prompt,
)
from app.providers.vision.schemas import (
    LlmPlannerResult,
    LlmPromptArchitectResult,
    LlmQualityReport,
)

logger = logging.getLogger(__name__)


class OpenRouterVisualPlanner:
    name = "openrouter"

    def __init__(self, client: LlmClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._usage: LlmUsage | None = None

    @property
    def model(self) -> str | None:
        return self._settings.planner_model

    async def plan_directions(
        self,
        image: bytes,
        context: PlannerContext,
        *,
        original: bytes | None = None,
    ) -> PlannerResult:
        frames = [_for_vision(image)]
        labels = ["approved_crop"]
        user = plan_user_prompt(context)
        if original and original != image:
            frames.append(_for_vision(original))
            labels.append("original_upload")
            user = (
                "Image 1 = APPROVED CROP. Image 2 = ORIGINAL UPLOAD (may contain UI).\n"
                + user
            )
        payload, trace = await self._complete(
            schema_name="creative_director",
            schema=strict_schema(LlmPlannerResult),
            model=LlmPlannerResult,
            system=planner_system(),
            user=user,
            images=tuple(frames),
            image_labels=labels,
        )
        quality = InputQuality(
            status=payload.input_quality.status,
            reasons=tuple(payload.input_quality.reasons),
        )
        analysis = _analysis_from(payload.reference_analysis)
        if analysis.reference_strategy == "needs_user_action" or analysis.brief_image_mismatch:
            quality = InputQuality(
                "needs_fix",
                quality.reasons or analysis.blocking_reasons or ("needs_user_action",),
            )
        directions = tuple(
            CampaignDirection(
                title_fa=item.title_fa.strip(),
                description_fa=item.description_fa.strip(),
                angle=item.angle.strip(),
                headline_fa=item.headline_fa.strip(),
                visual_direction=item.visual_direction.strip(),
                style_id=_known_style(item.style_id),
                template_id=_known_template(item.template_id),
                identity_constraints=tuple(
                    row.strip() for row in item.identity_constraints if row.strip()
                ),
                warning_fa=item.warning_fa.strip(),
                image_direction=item.image_direction.strip(),
                background_prompt=_ensure_no_text(item.background_prompt.strip()),
                text_safe_area=item.text_safe_area.strip() or "bottom",
                compatibility=compatibility(
                    _known_style(item.style_id), _known_template(item.template_id)
                ),
            )
            for item in payload.directions
        )
        return PlannerResult(
            product_visual_analysis=payload.product_visual_analysis.strip()
            or "visible product",
            product_type=payload.product_type.strip() or "product",
            visual_identity=tuple(
                row.strip() for row in payload.visual_identity if row.strip()
            ),
            identity_constraints=tuple(
                row.strip() for row in payload.identity_constraints if row.strip()
            ),
            unsuitable_style_ids=tuple(
                row for row in payload.unsuitable_style_ids if row in style_ids()
            ),
            unsuitable_template_ids=tuple(
                row
                for row in payload.unsuitable_template_ids
                if row in template_ids()
            ),
            input_quality=quality,
            directions=directions,
            forbidden_claims=tuple(
                row.strip() for row in payload.forbidden_claims if row.strip()
            ),
            reference_analysis=analysis,
            usage=self._usage,
            llm_trace=trace,
        )

    async def check_input_quality(
        self, image: bytes, context: PlannerContext
    ) -> InputQuality:
        del context
        if not image:
            return InputQuality("needs_fix", ("empty",))
        try:
            frame = Image.open(io.BytesIO(image))
        except Exception:
            return InputQuality("needs_fix", ("unreadable",))
        if min(frame.size) < 256:
            return InputQuality("needs_fix", ("too small",))
        return InputQuality("ok")

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: PlannerContext,
    ) -> QualityReport:
        frames = [_for_vision(reference), *(_for_vision(frame) for frame in candidates)]
        labels = [
            "cleaned_reference",
            *[f"candidate_{index + 1}" for index in range(len(candidates))],
        ]
        payload, trace = await self._complete(
            schema_name="visual_quality",
            schema=strict_schema(LlmQualityReport),
            model=LlmQualityReport,
            system=QUALITY_SYSTEM,
            user=quality_user_prompt(context, len(candidates)),
            images=tuple(frames),
            image_labels=labels,
        )
        rows: list[CandidateQuality] = []
        by_slot = {item.slot: item for item in payload.candidates}
        for index in range(len(candidates)):
            item = by_slot.get(index + 1)
            if item is None:
                rows.append(CandidateQuality(slot=index + 1, hard_failed=False))
                continue
            hard = _hard_fail(item)
            rows.append(
                CandidateQuality(
                    slot=item.slot,
                    hard_failed=hard,
                    reasons=tuple(item.reasons),
                    identity_recognizable=item.identity_recognizable,
                    no_random_text_or_logos=item.no_random_text_or_logos,
                    no_severe_artifacts=item.no_severe_artifacts,
                    no_unwanted_duplicates=item.no_unwanted_duplicates,
                    ad_composition=item.ad_composition,
                    text_safe_space=item.text_safe_space,
                    identity_quality=_score(item.identity_quality),
                    style_adherence=_score(item.style_adherence),
                    template_adherence=_score(item.template_adherence),
                    composition_quality=_score(item.composition_quality),
                    visual_attractiveness=_score(item.visual_attractiveness),
                    commercial_usefulness=_score(item.commercial_usefulness),
                    text_safe_space_quality=_score(item.text_safe_space_quality),
                )
            )
        return QualityReport(candidates=tuple(rows), usage=self._usage, llm_trace=trace)

    async def _complete(
        self,
        *,
        schema_name: str,
        schema: dict[str, Any],
        model: type,
        system: str,
        user: str,
        images: tuple[bytes, ...],
        llm_model: str | None = None,
        image_labels: list[str] | tuple[str, ...] = (),
    ) -> tuple[Any, LlmCallTrace]:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user},
                    *[_image_part(frame) for frame in images],
                ],
            },
        ]
        last_error: Exception | None = None
        attempts = max(1, self._settings.llm_max_retries + 1)
        chosen_model = (
            llm_model or self._settings.planner_model or self._settings.llm_model
        )
        labels = list(image_labels) or [
            f"image_{index + 1}" for index in range(len(images))
        ]
        for _ in range(attempts):
            try:
                result = await self._client.complete_json(
                    messages=messages,
                    schema_name=schema_name,
                    schema=schema,
                    model=chosen_model,
                )
            except Exception as error:
                last_error = error
                continue
            self._usage = result.usage
            try:
                payload = model.model_validate(parse_json_object(result.content))
            except (ValueError, ValidationError) as error:
                last_error = error
                logger.warning("visual planner json invalid: %s", error)
                continue
            trace = LlmCallTrace(
                name=schema_name,
                model=chosen_model,
                system=system,
                user=user,
                images=tuple(
                    llm_image_ref(
                        frame,
                        labels[index] if index < len(labels) else f"image_{index + 1}",
                    )
                    for index, frame in enumerate(images)
                ),
                output=result.content,
                usage=llm_usage_dict(result.usage),
            )
            return payload, trace
        raise last_error or generation_failed()


class OpenRouterPromptArchitect:
    name = "openrouter"

    def __init__(self, client: LlmClient, settings: Settings) -> None:
        self._planner = OpenRouterVisualPlanner(client, settings)
        self._settings = settings

    @property
    def model(self) -> str | None:
        return self._settings.architect_model

    async def plan_candidates(
        self,
        cleaned: bytes,
        context: ArchitectContext,
        *,
        original: bytes | None = None,
    ) -> PromptArchitectResult:
        frames = [_for_vision(cleaned)]
        labels = ["cleaned_reference"]
        user = (
            "Image 1 = CLEANED reference (this is what the image model will see).\n"
            + architect_user_prompt(context)
        )
        if original and original != cleaned:
            frames.append(_for_vision(original))
            labels.append("original_dirty")
            user = (
                "Image 1 = CLEANED reference (image model input). "
                "Image 2 = DIRTY/ORIGINAL (context only; do not reproduce UI).\n"
                + architect_user_prompt(context)
            )
        payload, trace = await self._planner._complete(
            schema_name="prompt_architect",
            schema=strict_schema(LlmPromptArchitectResult),
            model=LlmPromptArchitectResult,
            system=ARCHITECT_SYSTEM,
            user=user,
            images=tuple(frames),
            llm_model=self._settings.architect_model,
            image_labels=labels,
        )
        return _architect_from(payload, self._planner._usage, trace)


def _architect_from(
    payload: Any,
    usage: LlmUsage | None,
    trace: LlmCallTrace | None = None,
) -> PromptArchitectResult:
    seen_slots: set[int] = set()
    seen_intent: set[str] = set()
    rows: list[ArchitectCandidate] = []
    for item in payload.candidates:
        if item.slot in seen_slots or item.intention in seen_intent:
            continue
        seen_slots.add(item.slot)
        seen_intent.add(item.intention)
        pose = item.composition.human_or_pose.strip()
        rows.append(
            ArchitectCandidate(
                slot=int(item.slot),
                intention=item.intention,
                composition=ArchitectComposition(
                    camera=item.composition.camera.strip(),
                    product_scale=item.composition.product_scale.strip(),
                    product_position=item.composition.product_position.strip(),
                    human_or_pose=pose,
                    foreground=item.composition.foreground.strip(),
                    background=item.composition.background.strip(),
                    environment=item.composition.environment.strip(),
                    depth=item.composition.depth.strip(),
                    text_safe_area=item.composition.text_safe_area.strip(),
                ),
                lighting=item.lighting.strip(),
                palette=item.palette.strip(),
                relevant_props=tuple(
                    row.strip() for row in item.relevant_props if row.strip()
                ),
                must_preserve=tuple(
                    row.strip() for row in item.must_preserve if row.strip()
                ),
                must_avoid=tuple(row.strip() for row in item.must_avoid if row.strip()),
                image_prompt=item.image_prompt.strip(),
            )
        )
    if len(rows) != 3:
        raise generation_failed()
    return PromptArchitectResult(
        reference_summary=payload.reference_summary.strip(),
        identity_priority=tuple(
            IdentityFeature(item.feature.strip(), item.importance)
            for item in payload.identity_priority
            if item.feature.strip()
        ),
        art_direction={
            "visual_thesis": payload.art_direction.visual_thesis.strip(),
            "product_role": payload.art_direction.product_role.strip(),
            "style_execution": payload.art_direction.style_execution.strip(),
            "template_execution": payload.art_direction.template_execution.strip(),
            "palette_strategy": payload.art_direction.palette_strategy.strip(),
            "typography_safe_area": payload.art_direction.typography_safe_area.strip(),
        },
        candidates=tuple(sorted(rows, key=lambda row: row.slot)),
        usage=usage,
        llm_trace=trace,
    )


def _analysis_from(payload: Any) -> ReferenceAnalysis:
    crop = None
    if payload.has_recommended_crop:
        crop = CropBox(
            x=float(payload.recommended_crop.x),
            y=float(payload.recommended_crop.y),
            width=float(payload.recommended_crop.width),
            height=float(payload.recommended_crop.height),
        )
    return ReferenceAnalysis(
        cleanliness=payload.cleanliness,
        product_visibility=payload.product_visibility,
        screenshot_ui_present=payload.screenshot_ui_present,
        watermark_present=payload.watermark_present,
        multiple_products=payload.multiple_products,
        person_present=payload.person_present,
        useful_context_present=payload.useful_context_present,
        contamination_description=tuple(
            row.strip() for row in payload.contamination_description if row.strip()
        ),
        reference_strategy=payload.reference_strategy,
        recommended_crop=crop,
        preserve_context_reason=payload.preserve_context_reason.strip(),
        blocking_reasons=tuple(
            row.strip() for row in payload.blocking_reasons if row.strip()
        ),
        brief_image_mismatch=payload.brief_image_mismatch,
    )


def _score(value: int) -> int:
    return min(5, max(1, int(value)))


def _hard_fail(item: Any) -> bool:
    if item.hard_failed:
        return True
    return not (
        item.identity_recognizable
        and item.no_random_text_or_logos
        and item.no_severe_artifacts
        and item.ad_composition
    )


def _known_style(value: str) -> str:
    return value if value in style_ids() else "photoreal_commercial"


def _known_template(value: str) -> str:
    return value if value in template_ids() else "hero_product"


def _ensure_no_text(prompt: str) -> str:
    if "no text" in prompt.lower():
        return prompt
    return f"{prompt.rstrip(',')}, no text"


_VISION_EDGE = 1024


def _for_vision(content: bytes) -> bytes:
    """Shrink the crop before the multimodal planner call."""
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception:
        return content
    image.thumbnail((_VISION_EDGE, _VISION_EDGE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80, optimize=True)
    return buffer.getvalue()


def _image_part(content: bytes) -> dict[str, Any]:
    kind = "image/png" if content.startswith(b"\x89PNG") else "image/jpeg"
    encoded = base64.b64encode(content).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{kind};base64,{encoded}"},
    }
