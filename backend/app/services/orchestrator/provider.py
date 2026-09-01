"""Orchestrator LLM: stub fixtures in tests, OpenRouter in production."""

from __future__ import annotations

import logging
import re
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.llm.openrouter.client import OpenRouterClient, parse_json_object
from app.services.orchestrator.context import BoundedChatContext
from app.services.orchestrator.language import artifact_language, reply_language
from app.services.orchestrator.prompt import ORCHESTRATOR_SYSTEM_PROMPT
from app.services.orchestrator.schema import ORCHESTRATOR_SCHEMA, OrchestratorDecision
from app.services.orchestrator.texts import (
    ACK,
    CLARIFY_IMAGE,
    GENERIC_CHAT,
    UNSUPPORTED,
)

logger = logging.getLogger(__name__)

_stub_calls = 0

_UNSUPPORTED = re.compile(
    r"آهنگ|موزیک|موسیقی|\bmusic\b|\bsong\b|ویدیو|\bvideo\b|صدا|\bvoice\b|زیرنویس|\bsubtitle\b",
    re.IGNORECASE,
)
_EDU = re.compile(
    r"آموزشی|کلاس|درس|تدریس|معلم|دانش[\s‌]?آموز|اعشار|کسر|educational|lesson|teach",
    re.IGNORECASE,
)
_ADS = re.compile(
    r"تبلیغ|\bads?\b|advertis|کمپین|کپشن\s*اینستا|instagram\s+ad",
    re.IGNORECASE,
)
_IMAGE = re.compile(
    r"(تصویر|عکس|illustration|image).{0,12}(بساز|بکش|generate)"
    r"|(بساز|بکش|generate).{0,12}(تصویر|عکس|illustration|image)"
    r"|یه\s+تصویر\s+بساز",
    re.IGNORECASE,
)
_VAGUE = re.compile(
    r"^(یه\s+چیزی|something)\s+(برام\s+)?بساز\.?$",
    re.IGNORECASE,
)


class OrchestratorProvider(Protocol):
    async def complete(self, context: BoundedChatContext) -> OrchestratorDecision: ...


def stub_call_count() -> int:
    return _stub_calls


def reset_stub_calls() -> None:
    global _stub_calls
    _stub_calls = 0


def get_orchestrator_provider() -> OrchestratorProvider:
    settings = get_settings()
    if settings.content_provider == "stub":
        return StubOrchestratorProvider()
    return OpenRouterOrchestratorProvider()


class StubOrchestratorProvider:
    """Keyword routing. No OpenRouter. Used when CONTENT_PROVIDER=stub."""

    async def complete(self, context: BoundedChatContext) -> OrchestratorDecision:
        global _stub_calls
        _stub_calls += 1
        text = context.latest_user_text or ""
        lang = reply_language(text)
        art = artifact_language(text)
        if _UNSUPPORTED.search(text):
            return _decision(
                "unsupported", lang, art, assistant_message=UNSUPPORTED[lang]
            )
        if _VAGUE.search(text.strip()):
            return _decision(
                "clarify",
                lang,
                art,
                assistant_message=CLARIFY_IMAGE[lang],
                needs_clarification=True,
            )
        if _EDU.search(text):
            return _decision("education", lang, art, preamble=ACK["education"][lang])
        if _ADS.search(text):
            return _decision(
                "advertising", lang, art, preamble=ACK["advertising"][lang]
            )
        if _IMAGE.search(text):
            return _decision(
                "general_image", lang, art, preamble=ACK["general_image"][lang]
            )
        return _decision(
            "general_chat",
            lang,
            art,
            assistant_message=_chat_reply(text, lang),
        )


def _chat_reply(text: str, lang: str) -> str:
    lowered = text.lower()
    if "کپشن" in text or "caption" in lowered:
        if lang == "en":
            return "Here’s a short caption you can post."
        return "یه کپشن کوتاه: امروز یه کار جدید از راه رسید."
    if lang == "en":
        return "Tell me what you’d like to make — an ad, a teaching post, or an image."
    return GENERIC_CHAT["fa"]


def _decision(
    route: str,
    lang: str,
    art: str | None,
    *,
    preamble: str | None = None,
    assistant_message: str | None = None,
    needs_clarification: bool = False,
) -> OrchestratorDecision:
    return OrchestratorDecision(
        route=route,  # type: ignore[arg-type]
        reply_language=lang,  # type: ignore[arg-type]
        artifact_language=art,  # type: ignore[arg-type]
        assistant_preamble=preamble,
        assistant_message=assistant_message,
        needs_clarification=needs_clarification,
        clarification_question=assistant_message if needs_clarification else None,
        generation_instruction=None,
        requested_image_count=None,
        orchestrator_called=True,
    )


class OpenRouterOrchestratorProvider:
    async def complete(self, context: BoundedChatContext) -> OrchestratorDecision:
        from app.services.orchestrator.context import context_as_user_payload

        settings = get_settings()
        client = OpenRouterClient(settings)
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": context_as_user_payload(context)},
        ]
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                result = await client.complete_json(
                    messages=messages,
                    schema_name="afarin_orchestrator",
                    schema=ORCHESTRATOR_SCHEMA,
                    model=settings.chat_orchestrator_model_resolved,
                )
                data = parse_json_object(result.content)
                return OrchestratorDecision.model_validate(data)
            except Exception as error:
                last_error = error
                logger.warning("orchestrator JSON failed: %s", error)
        raise last_error or generation_failed()
