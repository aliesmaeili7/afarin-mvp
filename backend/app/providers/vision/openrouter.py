from __future__ import annotations

import base64
import io
import logging
from typing import Any

from PIL import Image
from pydantic import ValidationError

from app.content.visual_catalog import style_ids, template_ids
from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter.client import LlmClient, parse_json_object
from app.providers.llm.openrouter.schemas import strict_schema
from app.providers.vision.base import (
    CampaignDirection,
    CandidateQuality,
    InputQuality,
    PlannerContext,
    PlannerResult,
    QualityReport,
)
from app.providers.vision.prompts import (
    QUALITY_SYSTEM,
    plan_user_prompt,
    planner_system,
    quality_user_prompt,
)
from app.providers.vision.schemas import LlmPlannerResult, LlmQualityReport

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
        self, image: bytes, context: PlannerContext
    ) -> PlannerResult:
        payload = await self._complete(
            schema_name="creative_director",
            schema=strict_schema(LlmPlannerResult),
            model=LlmPlannerResult,
            system=planner_system(),
            user=plan_user_prompt(context),
            images=(_for_vision(image),),
        )
        quality = InputQuality(
            status=payload.input_quality.status,
            reasons=tuple(payload.input_quality.reasons),
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
            usage=self._usage,
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
        payload = await self._complete(
            schema_name="visual_quality",
            schema=strict_schema(LlmQualityReport),
            model=LlmQualityReport,
            system=QUALITY_SYSTEM,
            user=quality_user_prompt(context, len(candidates)),
            images=(
                _for_vision(reference),
                *(_for_vision(frame) for frame in candidates),
            ),
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
                )
            )
        return QualityReport(candidates=tuple(rows), usage=self._usage)

    async def _complete(
        self,
        *,
        schema_name: str,
        schema: dict[str, Any],
        model: type,
        system: str,
        user: str,
        images: tuple[bytes, ...],
    ) -> Any:
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
        for _ in range(attempts):
            try:
                result = await self._client.complete_json(
                    messages=messages,
                    schema_name=schema_name,
                    schema=schema,
                    model=self._settings.planner_model or self._settings.llm_model,
                )
            except Exception as error:
                last_error = error
                continue
            self._usage = result.usage
            try:
                return model.model_validate(parse_json_object(result.content))
            except (ValueError, ValidationError) as error:
                last_error = error
                logger.warning("visual planner json invalid: %s", error)
        raise last_error or generation_failed()


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
