import logging
from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.llm.base import ContentProvider, LlmUsage
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from app.providers.llm.stub import StubContentProvider

logger = logging.getLogger(__name__)

_override: ContentProvider | None = None


def set_content_provider(provider: ContentProvider | None) -> None:
    """Tests inject a fake client this way. Production never calls it."""
    global _override
    _override = provider


def get_content_provider() -> ContentProvider:
    """Provider selection lives in configuration, never in business logic (spec §23)."""
    if _override is not None:
        return _override

    settings = get_settings()
    if settings.content_provider == "stub":
        return StubContentProvider()
    if settings.content_provider == "openrouter":
        if not settings.openrouter_api_key:
            logger.error("OPENROUTER_API_KEY is empty; refusing to stub")
            raise generation_failed()
        return _openrouter_provider()
    raise ValueError(f"unknown content provider: {settings.content_provider}")


@lru_cache
def _openrouter_provider() -> OpenRouterContentProvider:
    settings = get_settings()
    return OpenRouterContentProvider(OpenRouterClient(settings), settings)


__all__ = [
    "ContentProvider",
    "LlmUsage",
    "StubContentProvider",
    "get_content_provider",
    "set_content_provider",
]
