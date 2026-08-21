import json
from decimal import Decimal

from app.core.errors import ApiError
from app.providers.image.base import ImageRequest, ImageResult, ImageUsage
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
        messages: list[dict],
        schema_name: str,
        schema: dict,
        model: str | None = None,
    ) -> CompletionResult:
        self.calls.append(
            {
                "messages": messages,
                "schema_name": schema_name,
                "schema": schema,
                "model": model,
            }
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


def three_directions() -> dict:
    base = {
        "identity_constraints": ["keep colors"],
        "warning_fa": "",
        "text_safe_area": "bottom",
        "background_prompt": "empty studio, no text",
    }
    return {
        "product_visual_analysis": "a visible product on a clean crop",
        "product_type": "hoodie",
        "visual_identity": ["navy fabric"],
        "identity_constraints": ["keep silhouette"],
        "unsuitable_style_ids": [],
        "unsuitable_template_ids": [],
        "input_quality": {"status": "ok", "reasons": []},
        "directions": [
            {
                **base,
                "title_fa": "واقعی و واضح",
                "description_fa": "محصول در مرکز",
                "angle": "editorial hero",
                "headline_fa": "کیفیتی که فرقش حس می‌شه",
                "visual_direction": "نور استودیویی",
                "style_id": "photoreal_commercial",
                "template_id": "hero_product",
                "image_direction": "clean studio hero",
            },
            {
                **base,
                "title_fa": "تصویرسازی",
                "description_fa": "صحنه کشیده‌شده",
                "angle": "illustrated lifestyle",
                "headline_fa": "یه حال و هوای تازه",
                "visual_direction": "تصویرسازی رنگی",
                "style_id": "anime",
                "template_id": "illustrated_scene",
                "image_direction": "illustrated scene around the product",
            },
            {
                **base,
                "title_fa": "ایده غیرمنتظره",
                "description_fa": "مقیاس سوررئال",
                "angle": "surreal scale",
                "headline_fa": "بزرگ‌تر از چیزی که فکر می‌کنی",
                "visual_direction": "غول در شهر کوچک",
                "style_id": "surreal",
                "template_id": "giant_miniature_world",
                "image_direction": "giant product in a miniature city",
            },
        ],
        "forbidden_claims": [],
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


class FakeImageProvider:
    """Returns queued scene bytes. Never touches the network."""

    name = "fake"
    model = "fake-scene"

    def __init__(
        self,
        results: list[ImageResult | Exception] | Exception | None = None,
    ) -> None:
        self.results = list(results) if isinstance(results, list) else []
        self.error = results if isinstance(results, Exception) else None
        self.calls: list[ImageRequest] = []

    async def generate(self, request: ImageRequest) -> ImageResult:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        if self.results:
            item = self.results.pop(0)
            if isinstance(item, BaseException):
                raise item
            if request.n > 1 and not item.contents:
                frames = tuple(
                    _tiny_jpeg(len(self.calls) + index) for index in range(request.n)
                )
                return ImageResult(
                    content=frames[0],
                    contents=frames,
                    media_type=item.media_type,
                    usage=item.usage,
                )
            return item
        count = max(1, request.n)
        frames = tuple(_tiny_jpeg(len(self.calls) + index) for index in range(count))
        return ImageResult(
            content=frames[0],
            contents=frames,
            media_type="image/jpeg",
            usage=ImageUsage(
                latency_ms=4,
                cost_usd=Decimal("0.04") * count,
                model=self.model,
            ),
        )


def _tiny_jpeg(variant: int = 0) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    color = ((30 + variant * 47) % 256, (40 + variant * 19) % 256, 50)
    Image.new("RGB", (8, 10), color).save(buffer, format="JPEG")
    return buffer.getvalue()

