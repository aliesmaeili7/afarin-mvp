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
        count = max(1, request.n)
        frames = tuple(
            _jpeg_for(request.aspect_ratio, tone + index * 17)
            for index in range(count)
        )
        return ImageResult(
            content=frames[0],
            contents=frames,
            media_type="image/jpeg",
            usage=ImageUsage(
                latency_ms=1,
                cost_usd=Decimal("0"),
                model=self.model,
            ),
        )


def _jpeg_for(aspect: str, tone: int) -> bytes:
    if aspect == "9:16":
        return _jpeg(9, 16, (36, 28 + tone % 80, 56))
    return _jpeg(8, 10, (48, 40 + tone % 80, 72))
