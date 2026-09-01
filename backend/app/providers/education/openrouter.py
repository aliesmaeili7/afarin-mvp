from __future__ import annotations

import logging

from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.education.base import (
    EducationalAgentContext,
    EducationalPostResult,
    EducationalTheme,
)
from app.providers.education.prompts import (
    educational_agent_system,
    educational_user_prompt,
)
from app.providers.education.schemas import LlmEducationalPostResult
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter.client import LlmClient, parse_json_object
from app.providers.llm.openrouter.schemas import strict_schema
from app.providers.vision.base import LlmCallTrace, llm_usage_dict

logger = logging.getLogger(__name__)

SCHEMA_NAME = "educational_agent"


class OpenRouterEducationalAgent:
    """Text-only, so no image parts and no vision downscaling."""

    name = "openrouter"

    def __init__(self, client: LlmClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @property
    def model(self) -> str | None:
        return self._settings.educational_agent_model_resolved

    async def create_post(
        self,
        context: EducationalAgentContext,
        *,
        correction: str | None = None,
    ) -> EducationalPostResult:
        system = educational_agent_system()
        user = educational_user_prompt(context, correction=correction)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        chosen_model = self._settings.educational_agent_model_resolved
        schema = strict_schema(LlmEducationalPostResult)
        attempts = max(1, self._settings.llm_max_retries + 1)
        last_error: Exception | None = None
        usage: LlmUsage | None = None
        for _ in range(attempts):
            try:
                completion = await self._client.complete_json(
                    messages=messages,
                    schema_name=SCHEMA_NAME,
                    schema=schema,
                    model=chosen_model,
                )
            except Exception as error:
                last_error = error
                continue
            usage = completion.usage
            try:
                payload = LlmEducationalPostResult.model_validate(
                    parse_json_object(completion.content)
                )
            except (ValueError, ValidationError) as error:
                last_error = error
                snippet = completion.content or ""
                logger.warning(
                    "educational agent json invalid: %s chars=%s head=%r",
                    error,
                    len(snippet),
                    snippet[:160],
                )
                continue
            trace = LlmCallTrace(
                name=SCHEMA_NAME,
                model=chosen_model,
                system=system,
                user=user,
                output=completion.content,
                usage=llm_usage_dict(completion.usage),
            )
            return result_from(payload, usage=usage, trace=trace)
        raise last_error or generation_failed()


def result_from(
    payload: LlmEducationalPostResult,
    *,
    usage: LlmUsage | None = None,
    trace: LlmCallTrace | None = None,
) -> EducationalPostResult:
    """Maps validated JSON onto the domain dataclasses, trimming as it goes."""
    theme = payload.theme
    return EducationalPostResult(
        language=payload.language,
        final_prompt=payload.final_prompt.strip(),
        theme=EducationalTheme(
            name_suggestion=theme.name_suggestion.strip(),
            primary_colors=tuple(
                color.strip() for color in theme.primary_colors if color.strip()
            ),
            secondary_colors=tuple(
                color.strip()
                for color in theme.secondary_colors
                if color.strip()
            ),
            illustration_style=theme.illustration_style.strip(),
            mood=theme.mood.strip(),
            lighting=theme.lighting.strip(),
            shape_language=theme.shape_language.strip(),
            decorative_motifs=tuple(
                row.strip() for row in theme.decorative_motifs if row.strip()
            ),
        ),
        theme_style_notes=_clean(payload.theme_style_notes),
        safety_notes=_clean(payload.safety_notes),
        usage=usage,
        llm_trace=trace,
    )


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None
