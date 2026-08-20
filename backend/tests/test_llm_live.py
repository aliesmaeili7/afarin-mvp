"""One real OpenRouter call. Skipped unless OPENROUTER_API_KEY is set."""

import os
import re

import pytest

from app.content.context import CopyContext
from app.core.config import Settings
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.llm.openrouter.provider import OpenRouterContentProvider

pytestmark = pytest.mark.live

PERSIAN = re.compile(r"[\u0600-\u06FF]")


@pytest.fixture
def live_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        pytest.skip("OPENROUTER_API_KEY is not set")
    return key


async def test_live_concepts_are_persian_and_length_three(live_key: str) -> None:
    settings = Settings(
        content_provider="openrouter",
        openrouter_api_key=live_key,
        llm_model=os.environ.get("LLM_MODEL", "openai/gpt-5-mini"),
        llm_max_retries=1,
        llm_timeout_seconds=60,
    )
    provider = OpenRouterContentProvider(OpenRouterClient(settings), settings)
    drafts = await provider.build_concepts(
        CopyContext(
            product_name="زعفران ممتاز",
            description="یک گرمی مناسب هدیه",
            price_text="۳۹۹ هزار تومان",
            benefit="عطر قوی",
            brand_name="آرین",
            audience="هدیه",
            objective="sell_product",
            style="luxury",
            round=0,
        )
    )
    assert len(drafts) == 3
    for draft in drafts:
        assert PERSIAN.search(draft.headline_fa)
        assert PERSIAN.search(draft.title_fa)
        assert "no text" in draft.background_prompt.lower()
        assert draft.background_id
