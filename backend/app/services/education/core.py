"""
Educational generation, without a database in sight.

Production and the eval harness both call this, which is what keeps the eval
honest: it exercises the same agent call, the same validation and the same
image request the real endpoint uses.

The whole path is: prompt -> agent -> validate -> one image. There is no
planner, no prompt compiler, no candidate selection and no text overlay.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.education import get_educational_agent
from app.providers.education.base import (
    EducationalAgent,
    EducationalAgentContext,
    EducationalPostResult,
)
from app.providers.education.validate import (
    EducationalValidation,
    correction_user_block,
    validate_educational_result,
)
from app.providers.image import get_image_provider
from app.providers.image.base import ImageRequest, ImageResult
from app.providers.llm.base import LlmUsage, merge_llm_usage

#: Phase 1 renders one square Instagram post and nothing else.
EDUCATION_ASPECT = "1:1"
EDUCATION_IMAGE_COUNT = 1


@dataclass(frozen=True, slots=True)
class PlannedPost:
    result: EducationalPostResult
    validation: EducationalValidation
    retry_used: bool

    def as_dict(self) -> dict[str, Any]:
        payload = self.result.as_dict()
        payload["validation"] = self.validation.as_dict(
            retry_used=self.retry_used
        )
        if self.result.llm_trace is not None:
            payload["llm_trace"] = self.result.llm_trace.as_dict()
        return payload


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    content: bytes
    media_type: str
    result: ImageResult


async def plan_validated_post(
    *,
    user_prompt: str,
    selected_theme: dict[str, Any] | None = None,
    agent: EducationalAgent | None = None,
) -> PlannedPost:
    """
    One agent call, and at most one correction round.

    A second invalid response fails here, before any image is requested, so a
    malformed plan can never cost an image generation.
    """
    active = agent or get_educational_agent()
    context = EducationalAgentContext(
        user_prompt=user_prompt,
        selected_theme=selected_theme,
        aspect=EDUCATION_ASPECT,
    )
    theme_was_selected = selected_theme is not None

    first = await active.create_post(context)
    validation = validate_educational_result(
        first, theme_was_selected=theme_was_selected
    )
    if validation.ok:
        return PlannedPost(result=first, validation=validation, retry_used=False)

    second = await active.create_post(
        context, correction=correction_user_block(validation.errors)
    )
    retry_validation = validate_educational_result(
        second, theme_was_selected=theme_was_selected
    )
    merged = merge_llm_usage(first.usage, second.usage)
    result = _with_usage(second, merged)
    if not retry_validation.ok:
        raise generation_failed()
    return PlannedPost(result=result, validation=retry_validation, retry_used=True)


async def generate_post_image(final_prompt: str) -> GeneratedImage:
    """
    Exactly one image, from the agent's prompt byte for byte.

    No references: an educational post is drawn from an idea, not from a
    product photo, so there is nothing to send.
    """
    provider = get_image_provider()
    settings = get_settings()
    request = ImageRequest(
        prompt=final_prompt,
        aspect_ratio=EDUCATION_ASPECT,
        references=(),
        n=EDUCATION_IMAGE_COUNT,
        model=settings.educational_image_model_resolved,
    )
    result = await provider.generate(request)
    frames = result.images()
    if not frames:
        raise generation_failed()
    return GeneratedImage(
        content=frames[0], media_type=result.media_type, result=result
    )


@dataclass(frozen=True, slots=True)
class TimedRun:
    """
    Wall clock for the whole run.

    Deliberately one perf_counter delta rather than a sum of provider
    latencies, so educational and advertising timings mean the same thing.
    """

    started: float

    @classmethod
    def start(cls) -> TimedRun:
        return cls(started=time.perf_counter())

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)


def listing_title(prompt: str, *, limit: int = 80) -> str:
    """Dashboard label. Derived from the request, not from ad copy fields."""
    compact = " ".join((prompt or "").split())
    return compact[:limit]


def _with_usage(
    result: EducationalPostResult, usage: LlmUsage | None
) -> EducationalPostResult:
    if usage is None or result.usage is usage:
        return result
    return EducationalPostResult(
        language=result.language,
        final_prompt=result.final_prompt,
        theme=result.theme,
        theme_style_notes=result.theme_style_notes,
        safety_notes=result.safety_notes,
        usage=usage,
        llm_trace=result.llm_trace,
    )
