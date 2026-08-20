"""One real OpenRouter image call. Skipped unless OPENROUTER_API_KEY is set."""

import io
import os

import pytest
from PIL import Image

from app.core.config import Settings
from app.providers.image.base import ImageRequest
from app.providers.image.openrouter.client import OpenRouterImageClient
from app.providers.image.openrouter.provider import OpenRouterImageProvider
from app.providers.image.prompts import build_scene_prompt

pytestmark = pytest.mark.live


@pytest.fixture
def live_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        pytest.skip("OPENROUTER_API_KEY is not set")
    return key


async def test_live_empty_scene_is_a_raster_image(live_key: str) -> None:
    from types import SimpleNamespace

    settings = Settings(
        image_provider="openrouter",
        openrouter_api_key=live_key,
        image_model=os.environ.get("IMAGE_MODEL", "bytedance-seed/seedream-4.5"),
        image_max_retries=1,
        image_timeout_seconds=120,
    )
    provider = OpenRouterImageProvider(OpenRouterImageClient(settings), settings)
    prompt = build_scene_prompt(
        SimpleNamespace(
            visual_direction="soft daylight, generous negative space",
            background_prompt="empty marble countertop, morning light, no text",
        ),
        SimpleNamespace(visual_style="minimal"),
    )
    result = await provider.generate(
        ImageRequest(prompt=prompt, aspect_ratio="4:5", resolution="2K")
    )
    assert len(result.content) > 1000
    image = Image.open(io.BytesIO(result.content))
    assert image.size[0] > 8
    assert image.format in {"JPEG", "PNG", "WEBP"}
    print(
        f"live scene model={result.usage.model} size={image.size} "
        f"cost_usd={result.usage.cost_usd} format={image.format}"
    )
