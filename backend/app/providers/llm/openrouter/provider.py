from __future__ import annotations

import logging

from pydantic import ValidationError

from app.content.backgrounds import backgrounds_for_style
from app.content.concepts import ConceptDraft
from app.content.context import CopyContext, pick
from app.content.copy import CaptionSet, ReelConcept
from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter import prompts
from app.providers.llm.openrouter.client import LlmClient, parse_json_object
from app.providers.llm.openrouter.schemas import (
    LlmConcepts,
    LlmCopyPackage,
    LlmRewrite,
    captions_from,
    reel_from,
    strict_schema,
)

logger = logging.getLogger(__name__)


class OpenRouterContentProvider:
    """LLM-backed ContentProvider. Two campaign completions, plus rewrite."""

    name = "openrouter"

    def __init__(self, client: LlmClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._copy_cache: dict[tuple, LlmCopyPackage] = {}
        self._usage: LlmUsage | None = None

    @property
    def model(self) -> str | None:
        return self._settings.llm_model

    async def build_concepts(self, ctx: CopyContext) -> list[ConceptDraft]:
        payload = await self._complete(
            schema_name="campaign_concepts",
            schema=strict_schema(LlmConcepts),
            user=prompts.concepts_user_prompt(ctx),
            model=LlmConcepts,
        )
        backgrounds = backgrounds_for_style(ctx.style)
        drafts: list[ConceptDraft] = []
        for index, item in enumerate(payload.concepts):
            drafts.append(
                ConceptDraft(
                    title_fa=item.title_fa.strip(),
                    headline_fa=item.headline_fa.strip(),
                    description_fa=item.description_fa.strip(),
                    visual_direction=item.visual_direction.strip(),
                    background_prompt=_ensure_no_text(item.background_prompt.strip()),
                    background_id=pick(backgrounds, ctx.round + index),
                )
            )
        return drafts

    async def build_captions(self, ctx: CopyContext) -> CaptionSet:
        package = await self._copy_package(ctx)
        return captions_from(package)

    async def build_story_ideas(self, ctx: CopyContext) -> list[str]:
        package = await self._copy_package(ctx)
        return list(package.story_ideas)

    async def build_primary_cta(self, ctx: CopyContext) -> str:
        package = await self._copy_package(ctx)
        return package.cta_fa

    async def build_hashtags(self, ctx: CopyContext) -> str:
        package = await self._copy_package(ctx)
        return package.hashtags

    async def build_reel_concept(self, ctx: CopyContext) -> ReelConcept:
        package = await self._copy_package(ctx)
        return reel_from(package)

    async def build_subheadline(self, ctx: CopyContext) -> str:
        package = await self._copy_package(ctx)
        return package.subheadline_fa

    async def rewrite_text(
        self,
        ctx: CopyContext,
        *,
        intent: str,
        current: str,
        field: str,
    ) -> str:
        payload = await self._complete(
            schema_name="copy_rewrite",
            schema=strict_schema(LlmRewrite),
            user=prompts.rewrite_user_prompt(
                ctx, intent=intent, current=current, field=field
            ),
            model=LlmRewrite,
        )
        return payload.text_fa.strip()

    def consume_usage(self) -> LlmUsage | None:
        usage = self._usage
        self._usage = None
        return usage

    async def _copy_package(self, ctx: CopyContext) -> LlmCopyPackage:
        key = _cache_key(ctx)
        cached = self._copy_cache.get(key)
        if cached is not None:
            return cached
        payload = await self._complete(
            schema_name="campaign_copy",
            schema=strict_schema(LlmCopyPackage),
            user=prompts.copy_user_prompt(ctx),
            model=LlmCopyPackage,
        )
        self._copy_cache[key] = payload
        return payload

    async def _complete[T](
        self,
        *,
        schema_name: str,
        schema: dict,
        user: str,
        model: type[T],
    ) -> T:
        messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        last_error = "invalid output"
        attempts = 1 + max(0, self._settings.llm_max_retries)
        for attempt in range(attempts):
            result = await self._client.complete_json(
                messages=messages,
                schema_name=schema_name,
                schema=schema,
            )
            self._usage = result.usage
            try:
                parsed = parse_json_object(result.content)
                return model.model_validate(parsed)
            except (ValidationError, ValueError) as error:
                last_error = str(error)
                logger.info("llm schema miss attempt %s: %s", attempt + 1, last_error)
                messages = [
                    *messages,
                    {"role": "assistant", "content": result.content},
                    {
                        "role": "user",
                        "content": (
                            "خروجی با اسکیما نمی‌خواند. همان JSON را با این "
                            f"ایرادها اصلاح کن:\n{last_error[:1500]}"
                        ),
                    },
                ]
        logger.warning("llm output invalid after retries: %s", last_error)
        raise generation_failed()


def _cache_key(ctx: CopyContext) -> tuple:
    return (
        ctx.product_name,
        ctx.description,
        ctx.price_text,
        ctx.benefit,
        ctx.brand_name,
        ctx.audience,
        ctx.objective,
        ctx.style,
        ctx.round,
        ctx.selected_headline,
    )


def _ensure_no_text(prompt: str) -> str:
    if "no text" in prompt.lower():
        return prompt
    return f"{prompt.rstrip(',')}, no text"
