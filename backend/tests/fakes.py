import json
from decimal import Decimal

from app.core.errors import ApiError
from app.providers.llm.base import LlmUsage
from app.providers.llm.openrouter.client import CompletionResult


class FakeLlmClient:
    """Returns queued JSON payloads. Never touches the network."""

    def __init__(
        self, payloads: list[dict | Exception] | Exception | None = None
    ) -> None:
        self.payloads = list(payloads) if isinstance(payloads, list) else []
        self.error = payloads if isinstance(payloads, Exception) else None
        self.invalid_first = False
        self.invalid_json_first = False
        self.calls: list[dict] = []

    async def complete_json(
        self,
        *,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict,
    ) -> CompletionResult:
        self.calls.append(
            {"messages": messages, "schema_name": schema_name, "schema": schema}
        )
        if self.error is not None:
            raise self.error
        if self.invalid_first and len(self.calls) == 1:
            content = json.dumps({"not": "a valid payload"})
        elif self.invalid_json_first and len(self.calls) == 1:
            content = "not-json"
        elif self.payloads:
            item = self.payloads.pop(0)
            if isinstance(item, BaseException):
                raise item
            content = json.dumps(item)
        else:
            raise AssertionError("FakeLlmClient has no more payloads")
        return CompletionResult(
            content=content,
            usage=LlmUsage(
                prompt_tokens=11,
                completion_tokens=22,
                latency_ms=15,
                cost_usd=Decimal("0.0001"),
                model="openai/gpt-5-mini",
            ),
            raw={},
        )


def three_concepts() -> dict:
    return {
        "concepts": [
            {
                "title_fa": "هدیه شبانه",
                "headline_fa": "زعفران ممتاز قائنات، هدیه‌ای با عطر ایران",
                "description_fa": "نور نقطه‌ای روی محصول، حس لوکس و خاص.",
                "visual_direction": "پس‌زمینه تیره و نور طلایی",
                "background_prompt": "dark velvet studio, soft spotlight, no text",
            },
            {
                "title_fa": "سادگی گران",
                "headline_fa": "کیفیتی که فرقش حس می‌شه",
                "description_fa": "فضای خالی زیاد و تمرکز کامل روی محصول.",
                "visual_direction": "مینیمال تیره",
                "background_prompt": "minimal dark gradient, no text",
            },
            {
                "title_fa": "عطر بازار",
                "headline_fa": "از قائنات تا خونه‌ات",
                "description_fa": "حس بازار سنتی با بسته‌بندی مدرن.",
                "visual_direction": "رنگ زعفرانی و بافت پارچه",
                "background_prompt": "warm saffron textile backdrop, no text",
            },
        ]
    }


def copy_package() -> dict:
    return {
        "caption_short": "زعفران ممتاز قائنات ✨\nهمین حالا سفارش بده",
        "caption_friendly": "یه بسته زعفران که واقعاً عطر داره.",
        "caption_persuasive": "برای مهمونی یا هدیه، همین کافیه.",
        "story_ideas": ["موجود شد", "کدوم بسته‌بندی؟", "دایرکت بده"],
        "cta_fa": "همین حالا سفارش بده",
        "hashtags": "#زعفران #هدیه_ایرانی",
        "subheadline_fa": "بسته‌بندی هدیه و کیفیت صادراتی",
        "reel": {
            "hook_fa": "سه ثانیه وقت بده",
            "scenes_fa": ["نمای نزدیک", "استفاده واقعی", "بسته‌بندی"],
            "cta_fa": "دایرکت بده",
            "voiceover_fa": "زعفران ممتاز قائنات. همین حالا سفارش بده.",
            "duration_seconds": 12,
        },
    }


FAILED = ApiError(
    "generation_failed", "ساخت این بخش الان ممکن نشد. لطفاً دوباره امتحان کن."
)
