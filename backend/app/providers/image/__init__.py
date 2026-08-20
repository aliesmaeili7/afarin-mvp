import logging
from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.image.base import (
    ImageApiError,
    ImageProvider,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.openrouter.client import OpenRouterImageClient
from app.providers.image.openrouter.provider import OpenRouterImageProvider
from app.providers.image.stub import StubImageProvider

logger = logging.getLogger(__name__)

_override: ImageProvider | None = None


def set_image_provider(provider: ImageProvider | None) -> None:
    """Tests inject a fake client this way. Production never calls it."""
    global _override
    _override = provider


def get_image_provider() -> ImageProvider:
    """Provider selection lives in configuration, never in business logic (spec §23)."""
    if _override is not None:
        return _override

    settings = get_settings()
    if settings.image_provider == "stub":
        return StubImageProvider()
    if settings.image_provider == "openrouter":
        if not settings.openrouter_api_key:
            logger.error(
                "OPENROUTER_API_KEY is empty; refusing to stub image generation"
            )
            raise generation_failed()
        return _openrouter_provider()
    raise ValueError(f"unknown image provider: {settings.image_provider}")


@lru_cache
def _openrouter_provider() -> OpenRouterImageProvider:
    settings = get_settings()
    return OpenRouterImageProvider(OpenRouterImageClient(settings), settings)


__all__ = [
    "ImageApiError",
    "ImageProvider",
    "ImageRequest",
    "ImageResult",
    "ImageUsage",
    "StubImageProvider",
    "get_image_provider",
    "set_image_provider",
]
