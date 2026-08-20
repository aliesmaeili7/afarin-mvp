from app.core.config import Settings
from app.providers.image.base import ImageProvider, ImageRequest, ImageResult
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
        return await self._client.generate(request)
