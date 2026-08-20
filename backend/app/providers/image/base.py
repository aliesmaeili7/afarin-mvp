from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ImageRequest:
    prompt: str
    aspect_ratio: str
    resolution: str = "2K"
    output_format: str | None = None
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class ImageUsage:
    latency_ms: int
    cost_usd: Decimal | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ImageResult:
    content: bytes
    media_type: str
    usage: ImageUsage


class ImageApiError(Exception):
    """
    A provider HTTP failure with enough metadata to record on the job, and
    none of the API key. 4xx (except 429) is not retryable.
    """

    def __init__(
        self,
        *,
        status_code: int | None,
        provider_message: str,
        payload_keys: tuple[str, ...],
        retryable: bool,
    ) -> None:
        self.status_code = status_code
        self.provider_message = provider_message[:500]
        self.payload_keys = payload_keys
        self.retryable = retryable
        super().__init__(self.provider_message)

    def to_dict(self) -> dict:
        return {
            "http_status": self.status_code,
            "retryable": self.retryable,
            "provider_message": self.provider_message,
            "payload_keys": list(self.payload_keys),
        }


class ImageProvider:
    """
    Empty-scene generation. Campaign code never sends the product through this.

    Selected by IMAGE_PROVIDER; OpenRouter lives behind an implementation so
    swapping hosts does not touch services (spec §23).
    """

    name: str
    model: str | None

    async def generate(self, request: ImageRequest) -> ImageResult:
        raise NotImplementedError
