from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.vision.base import VisualPlanner
from app.providers.vision.stub import StubVisualPlanner

_override: VisualPlanner | None = None


def set_visual_planner(planner: VisualPlanner | None) -> None:
    global _override
    _override = planner


def get_visual_planner() -> VisualPlanner:
    if _override is not None:
        return _override
    settings = get_settings()
    if settings.content_provider == "stub":
        return StubVisualPlanner()
    if settings.content_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise generation_failed()
        return _openrouter_planner()
    raise ValueError(f"unknown content provider: {settings.content_provider}")


@lru_cache
def _openrouter_planner():
    from app.providers.vision.openrouter import OpenRouterVisualPlanner

    settings = get_settings()
    return OpenRouterVisualPlanner(OpenRouterClient(settings), settings)
