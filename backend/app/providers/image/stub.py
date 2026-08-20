import io
from decimal import Decimal

from PIL import Image

from app.providers.image.base import (
    ImageProvider,
    ImageRequest,
    ImageResult,
    ImageUsage,
)


def _jpeg(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


class StubImageProvider(ImageProvider):
    """Tiny fixture JPEGs. Used in tests and IMAGE_PROVIDER=stub."""

    name = "stub"
    model = "stub-scene"

    async def generate(self, request: ImageRequest) -> ImageResult:
        tone = sum(request.prompt.encode()) % 80
        if request.aspect_ratio == "9:16":
            content = _jpeg(9, 16, (36, 28 + tone, 56))
        else:
            content = _jpeg(8, 10, (48, 40 + tone, 72))
        return ImageResult(
            content=content,
            media_type="image/jpeg",
            usage=ImageUsage(
                latency_ms=1,
                cost_usd=Decimal("0"),
                model=self.model,
            ),
        )
