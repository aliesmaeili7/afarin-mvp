from __future__ import annotations

import base64
import io
import logging
from typing import Any

from PIL import Image
from pydantic import ValidationError

from app.content.visual_catalog import template_ids
from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter.client import LlmClient, parse_json_object
from app.providers.llm.openrouter.schemas import strict_schema
from app.providers.vision.base import (
    CampaignStrategy,
    CandidateQuality,
    ConceptCopy,
    ConceptIdentity,
    CreativeAgentContext,
    CreativeAgentResult,
    CreativeImage,
    LlmCallTrace,
    QualityContext,
    QualityReport,
    TextSafeArea,
    VisualPlan,
    llm_image_ref,
    llm_usage_dict,
)
from app.providers.vision.prompts import (
    QUALITY_SYSTEM,
    creative_agent_system,
    creative_user_prompt,
    quality_user_prompt,
)
from app.providers.vision.schemas import LlmCreativeAgentResult, LlmQualityReport

logger = logging.getLogger(__name__)


class OpenRouterCreativeAgent:
    name = "openrouter"

    def __init__(self, client: LlmClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._usage: LlmUsage | None = None

    @property
    def model(self) -> str | None:
        return self._settings.creative_agent_model_resolved

    async def create_campaign(
        self,
        image: bytes,
        context: CreativeAgentContext,
        *,
        correction: str | None = None,
    ) -> CreativeAgentResult:
        payload, trace = await self._complete(
            schema_name="creative_agent",
            schema=strict_schema(LlmCreativeAgentResult),
            model=LlmCreativeAgentResult,
            system=creative_agent_system(context.requested_image_count),
            user=creative_user_prompt(context, correction=correction),
            images=(_for_vision(image),),
            image_labels=["cleaned_reference"],
            llm_model=self._settings.creative_agent_model_resolved,
        )
        return _result_from(payload, self._usage, trace)

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: QualityContext,
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
            llm_model or self._settings.creative_agent_model_resolved
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
                snippet = result.content or ""
                logger.warning(
                    "creative agent json invalid: %s chars=%s head=%r tail=%r",
                    error,
                    len(snippet),
                    snippet[:160],
                    snippet[-160:] if snippet else "",
                )
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


def _result_from(
    payload: Any,
    usage: LlmUsage | None,
    trace: LlmCallTrace | None,
) -> CreativeAgentResult:
    known = set(template_ids())
    images: list[CreativeImage] = []
    for item in payload.images:
        template_id = item.visual_plan.template_id
        if template_id and template_id not in known:
            template_id = None
        secondary = (item.copy.on_image_secondary or "").strip() or None
        pose = (item.visual_plan.human_or_pose or "").strip() or None
        images.append(
            CreativeImage(
                concept_title=item.concept_title.strip(),
                creative_angle=item.creative_angle.strip(),
                visual_plan=VisualPlan(
                    template_id=template_id,
                    scene=item.visual_plan.scene.strip(),
                    composition=item.visual_plan.composition.strip(),
                    camera=item.visual_plan.camera.strip(),
                    lighting=item.visual_plan.lighting.strip(),
                    palette=item.visual_plan.palette.strip(),
                    product_role=item.visual_plan.product_role.strip(),
                    human_or_pose=pose,
                    text_safe_area=TextSafeArea(
                        position=item.visual_plan.text_safe_area.position.strip(),
                        description=item.visual_plan.text_safe_area.description.strip(),
                    ),
                ),
                identity=ConceptIdentity(
                    must_preserve=tuple(
                        row.strip()
                        for row in item.identity.must_preserve
                        if row.strip()
                    ),
                    must_not_generate=tuple(
                        row.strip()
                        for row in item.identity.must_not_generate
                        if row.strip()
                    ),
                ),
                final_prompt=item.final_prompt.strip(),
                copy=ConceptCopy(
                    on_image_headline=item.copy.on_image_headline.strip(),
                    on_image_secondary=secondary,
                    feed_caption=item.copy.feed_caption.strip(),
                    story_text=item.copy.story_text.strip(),
                    cta=item.copy.cta.strip(),
                    hashtags=tuple(
                        tag.strip() for tag in item.copy.hashtags if tag.strip()
                    ),
                ),
            )
        )
    return CreativeAgentResult(
        product_summary=payload.product_summary.strip(),
        campaign_strategy=CampaignStrategy(
            core_message=payload.campaign_strategy.core_message.strip(),
            audience_takeaway=payload.campaign_strategy.audience_takeaway.strip(),
            tone=payload.campaign_strategy.tone.strip(),
        ),
        images=tuple(images),
        usage=usage,
        llm_trace=trace,
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


_VISION_EDGE = 1024


def _for_vision(content: bytes) -> bytes:
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
