from __future__ import annotations

import base64
import logging
import re
import time
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.image.base import (
    ImageApiError,
    ImageRequest,
    ImageResult,
    ImageUsage,
)

logger = logging.getLogger(__name__)

_SECRET = re.compile(r"sk-[a-zA-Z0-9_-]{8,}")


class OpenRouterImageClient:
    """
    POST {llm_base_url}/images. Campaign code never imports this; the image
    provider does, so swapping hosts does not touch services.
    """

    def __init__(
        self, settings: Settings, http: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._http = http
        self._capabilities: dict[str, Any] | None = None

    async def generate(self, request: ImageRequest) -> ImageResult:
        if not self._settings.openrouter_api_key:
            raise generation_failed()

        payload = await self._payload(request)
        last_error: Exception | None = None
        attempts = max(1, self._settings.image_max_retries + 1)

        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                response = await self._client().post(
                    f"{self._settings.llm_base_url.rstrip('/')}/images",
                    headers=self._headers(),
                    json=payload,
                    timeout=self._settings.image_timeout_seconds,
                )
            except httpx.TimeoutException as error:
                last_error = ImageApiError(
                    status_code=None,
                    provider_message="image api timed out",
                    payload_keys=tuple(payload),
                    retryable=True,
                )
                logger.warning("image api timeout attempt %s", attempt + 1)
                if attempt + 1 < attempts:
                    continue
                raise last_error from error
            except httpx.HTTPError as error:
                last_error = ImageApiError(
                    status_code=None,
                    provider_message="image api network error",
                    payload_keys=tuple(payload),
                    retryable=True,
                )
                logger.warning("image api network error attempt %s", attempt + 1)
                if attempt + 1 < attempts:
                    continue
                raise last_error from error

            latency_ms = int((time.perf_counter() - started) * 1000)

            if response.status_code >= 400:
                message = _provider_message(response)
                retryable = _is_retryable(response.status_code)
                logger.warning(
                    "image api failed status=%s retryable=%s payload_keys=%s body=%s",
                    response.status_code,
                    retryable,
                    sorted(payload),
                    _safe_text(response.text),
                )
                error = ImageApiError(
                    status_code=response.status_code,
                    provider_message=message,
                    payload_keys=tuple(payload),
                    retryable=retryable,
                )
                if retryable and attempt + 1 < attempts:
                    last_error = error
                    continue
                raise error

            try:
                body = response.json()
            except ValueError as error:
                last_error = ImageApiError(
                    status_code=response.status_code,
                    provider_message="image api returned non-json",
                    payload_keys=tuple(payload),
                    retryable=True,
                )
                if attempt + 1 < attempts:
                    continue
                raise last_error from error

            content, media_type = await self._image_from(body)
            if not content:
                last_error = ImageApiError(
                    status_code=response.status_code,
                    provider_message="image api returned no image bytes",
                    payload_keys=tuple(payload),
                    retryable=True,
                )
                if attempt + 1 < attempts:
                    continue
                raise last_error

            return ImageResult(
                content=content,
                media_type=media_type,
                usage=_usage_from(body, latency_ms, self._settings.image_model),
            )

        raise last_error or generation_failed()

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._settings.openrouter_api_key}",
            "content-type": "application/json",
            "http-referer": self._settings.llm_http_referer,
            "x-title": self._settings.llm_app_title,
        }

    async def _payload(self, request: ImageRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._settings.image_model,
            "prompt": request.prompt,
        }
        params = await self._supported_parameters()
        resolution = (request.resolution or self._settings.image_resolution).strip()

        if params is None:
            # Discovery failed: send the fields Seedream 4.5 actually accepts.
            # Do not send 1K (too few pixels for 4:5 / 9:16) or output_format.
            payload["aspect_ratio"] = request.aspect_ratio
            if resolution and resolution != "1K":
                payload["resolution"] = resolution
            return payload

        if _enum_allows(params, "aspect_ratio", request.aspect_ratio) or not params:
            payload["aspect_ratio"] = request.aspect_ratio

        if resolution and resolution != "1K" and (
            not params or _enum_allows(params, "resolution", resolution)
        ):
            payload["resolution"] = resolution

        if request.output_format and _enum_allows(
            params, "output_format", request.output_format
        ):
            payload["output_format"] = request.output_format
        return payload

    async def _supported_parameters(self) -> dict[str, Any] | None:
        if self._capabilities is not None:
            return self._capabilities
        try:
            response = await self._client().get(
                f"{self._settings.llm_base_url.rstrip('/')}/images/models",
                headers=self._headers(),
                timeout=15.0,
            )
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            logger.warning(
                "image models discovery failed: %s %s",
                response.status_code,
                _safe_text(response.text),
            )
            return None
        try:
            body = response.json()
        except ValueError:
            return None
        models = body.get("data") if isinstance(body, dict) else None
        if not isinstance(models, list):
            return None
        wanted = self._settings.image_model
        match = next(
            (
                item
                for item in models
                if isinstance(item, dict) and item.get("id") == wanted
            ),
            None,
        )
        params = (match or {}).get("supported_parameters")
        if not isinstance(params, dict):
            self._capabilities = {}
            return self._capabilities
        self._capabilities = params
        return params

    async def _image_from(self, body: Any) -> tuple[bytes, str]:
        if not isinstance(body, dict):
            return b"", "image/jpeg"
        rows = body.get("data") or []
        if not rows or not isinstance(rows[0], dict):
            return b"", "image/jpeg"
        item = rows[0]
        encoded = item.get("b64_json") or item.get("b64")
        if isinstance(encoded, str) and encoded:
            raw = _decode_b64(encoded)
            return raw, _media_type_of(raw, item.get("content_type"))
        url = item.get("url") or (item.get("image_url") or {}).get("url")
        if isinstance(url, str) and url.startswith("data:"):
            raw = _decode_data_url(url)
            return raw, _media_type_of(raw, None)
        if isinstance(url, str) and url.startswith("http"):
            try:
                response = await self._client().get(
                    url, timeout=self._settings.image_timeout_seconds
                )
            except httpx.HTTPError:
                return b"", "image/jpeg"
            if response.status_code >= 400 or not response.content:
                return b"", "image/jpeg"
            return response.content, _media_type_of(
                response.content, response.headers.get("content-type")
            )
        return b"", "image/jpeg"

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient()
        return self._http


def _enum_allows(params: dict[str, Any], name: str, value: str) -> bool:
    spec = params.get(name)
    if not isinstance(spec, dict):
        return False
    values = spec.get("values")
    if isinstance(values, list):
        return value in values
    return False


def _is_retryable(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _provider_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return _safe_text(response.text) or f"http {response.status_code}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        if message:
            return _safe_text(str(message))
    if isinstance(error, str):
        return _safe_text(error)
    return _safe_text(response.text) or f"http {response.status_code}"


def _safe_text(value: str) -> str:
    return _SECRET.sub("[redacted]", value)[:500]


def _decode_b64(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.b64decode(padded, validate=False)
    except Exception:
        return b""


def _decode_data_url(url: str) -> bytes:
    _, _, rest = url.partition(",")
    return _decode_b64(rest)


def _media_type_of(content: bytes, hinted: str | None) -> str:
    if isinstance(hinted, str) and hinted.startswith("image/"):
        return hinted.split(";", 1)[0].strip()
    if content.startswith(b"\x89PNG"):
        return "image/png"
    if content.startswith(b"RIFF") and b"WEBP" in content[:16]:
        return "image/webp"
    return "image/jpeg"


def _usage_from(
    body: dict[str, Any], latency_ms: int, fallback_model: str
) -> ImageUsage:
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    cost = usage.get("cost")
    cost_usd: Decimal | None = None
    if isinstance(cost, int | float | str):
        try:
            cost_usd = Decimal(str(cost))
        except Exception:
            cost_usd = None
    model = body.get("model")
    return ImageUsage(
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        model=model if isinstance(model, str) else fallback_model,
        prompt_tokens=_as_int(usage.get("prompt_tokens")),
        completion_tokens=_as_int(usage.get("completion_tokens")),
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
