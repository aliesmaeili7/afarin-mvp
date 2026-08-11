from functools import lru_cache

from app.core.config import get_settings
from app.providers.llm.base import ContentProvider
from app.providers.llm.stub import StubContentProvider


@lru_cache
def get_content_provider() -> ContentProvider:
    """Provider selection lives in configuration, never in business logic (spec §23)."""
    provider = get_settings().content_provider
    if provider == "stub":
        return StubContentProvider()
    raise ValueError(f"unknown content provider: {provider}")


__all__ = ["ContentProvider", "StubContentProvider", "get_content_provider"]
