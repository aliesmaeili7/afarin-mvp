from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.education.base import (
    EducationalAgent,
    EducationalAgentContext,
    EducationalPostResult,
)
from app.providers.education.stub import StubEducationalAgent

__all__ = [
    "EducationalAgent",
    "EducationalAgentContext",
    "EducationalPostResult",
    "get_educational_agent",
    "set_educational_agent",
]

_override: EducationalAgent | None = None


def set_educational_agent(agent: EducationalAgent | None) -> None:
    global _override
    _override = agent


def get_educational_agent() -> EducationalAgent:
    if _override is not None:
        return _override
    settings = get_settings()
    if settings.content_provider == "stub":
        return StubEducationalAgent()
    if settings.content_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise generation_failed()
        return _openrouter_agent()
    raise ValueError(f"unknown content provider: {settings.content_provider}")


@lru_cache
def _openrouter_agent():
    from app.providers.education.openrouter import OpenRouterEducationalAgent
    from app.providers.llm.openrouter.client import OpenRouterClient

    settings = get_settings()
    return OpenRouterEducationalAgent(OpenRouterClient(settings), settings)
