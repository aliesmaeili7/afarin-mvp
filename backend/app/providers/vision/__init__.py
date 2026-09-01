from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.vision.base import CreativeAgent
from app.providers.vision.stub import StubCreativeAgent

_override: CreativeAgent | None = None


def set_creative_agent(agent: CreativeAgent | None) -> None:
    global _override
    _override = agent


def get_creative_agent() -> CreativeAgent:
    if _override is not None:
        return _override
    settings = get_settings()
    if settings.content_provider == "stub":
        return StubCreativeAgent()
    if settings.content_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise generation_failed()
        return _openrouter_agent()
    raise ValueError(f"unknown content provider: {settings.content_provider}")


@lru_cache
def _openrouter_agent():
    from app.providers.vision.openrouter import OpenRouterCreativeAgent

    settings = get_settings()
    return OpenRouterCreativeAgent(OpenRouterClient(settings), settings)
