from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import generation_failed
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.vision.base import PromptArchitect, VisualPlanner
from app.providers.vision.stub import StubPromptArchitect, StubVisualPlanner

_override: VisualPlanner | None = None
_architect_override: PromptArchitect | None = None


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


def set_prompt_architect(architect: PromptArchitect | None) -> None:
    global _architect_override
    _architect_override = architect


def get_prompt_architect() -> PromptArchitect:
    if _architect_override is not None:
        return _architect_override
    settings = get_settings()
    if settings.content_provider == "stub":
        return StubPromptArchitect()
    if settings.content_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise generation_failed()
        return _openrouter_architect()
    raise ValueError(f"unknown content provider: {settings.content_provider}")


@lru_cache
def _openrouter_planner():
    from app.providers.vision.openrouter import OpenRouterVisualPlanner

    settings = get_settings()
    return OpenRouterVisualPlanner(OpenRouterClient(settings), settings)


@lru_cache
def _openrouter_architect():
    from app.providers.vision.openrouter import OpenRouterPromptArchitect

    settings = get_settings()
    return OpenRouterPromptArchitect(OpenRouterClient(settings), settings)
