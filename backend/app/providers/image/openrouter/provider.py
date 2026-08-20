from dataclasses import replace
from decimal import Decimal

from app.core.config import Settings
from app.providers.image.base import (
    ImageProvider,
    ImageRequest,
    ImageResult,
    ImageUsage,
)
from app.providers.image.openrouter.client import OpenRouterImageClient


class OpenRouterImageProvider(ImageProvider):
    name = "openrouter"

    def __init__(self, client: OpenRouterImageClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @property
    def model(self) -> str | None:
        return self._settings.image_model

    async def generate(self, request: ImageRequest) -> ImageResult:
        first = await self._client.generate(request)
        frames = list(first.images())
        usages = [first.usage]
        while len(frames) < max(1, request.n):
            extra = await self._client.generate(replace(request, n=1))
            frames.extend(extra.images())
            usages.append(extra.usage)
        frames = frames[: max(1, request.n)]
        return ImageResult(
            content=frames[0],
            contents=tuple(frames),
            media_type=first.media_type,
            usage=_sum_usage(usages, first.usage.model),
        )


def _sum_usage(usages: list[ImageUsage], model: str | None) -> ImageUsage:
    cost: Decimal | None = None
    latency = 0
    prompt = 0
    completion = 0
    has_prompt = False
    has_completion = False
    for usage in usages:
        latency += usage.latency_ms
        if usage.cost_usd is not None:
            cost = (cost or Decimal("0")) + usage.cost_usd
        if usage.prompt_tokens is not None:
            prompt += usage.prompt_tokens
            has_prompt = True
        if usage.completion_tokens is not None:
            completion += usage.completion_tokens
            has_completion = True
    return ImageUsage(
        latency_ms=latency,
        cost_usd=cost,
        model=model,
        prompt_tokens=prompt if has_prompt else None,
        completion_tokens=completion if has_completion else None,
    )
