from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import generation_failed
from app.providers.llm.base import LlmUsage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    content: str
    usage: LlmUsage
    raw: dict[str, Any]


class LlmClient(Protocol):
    async def complete_json(
        self,
        *,
        messages: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> CompletionResult: ...


class OpenRouterClient:
    """
    Thin HTTP adapter. Campaign code never imports this; the content provider
    does, so swapping hosts or adding another vendor does not touch services.
    """

    def __init__(
        self, settings: Settings, http: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._http = http

    async def complete_json(
        self,
        *,
        messages: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> CompletionResult:
        if not self._settings.openrouter_api_key:
            raise generation_failed()

        payload = {
            "model": model or self._settings.llm_model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "usage": {"include": True},
        }
        headers = {
            "authorization": f"Bearer {self._settings.openrouter_api_key}",
            "content-type": "application/json",
            "http-referer": self._settings.llm_http_referer,
            "x-title": self._settings.llm_app_title,
        }

        started = time.perf_counter()
        try:
            response = await self._client().post(
                f"{self._settings.llm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self._settings.llm_timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise generation_failed() from error
        except httpx.HTTPError as error:
            raise generation_failed() from error

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            logger.warning(
                "openrouter chat failed status=%s body=%s",
                response.status_code,
                _safe_error_body(response),
            )
            raise generation_failed()

        try:
            body = response.json()
        except ValueError as error:
            raise generation_failed() from error

        content = _message_content(body)
        if not content:
            raise generation_failed()

        return CompletionResult(
            content=content,
            usage=_usage_from(
                body, latency_ms, model or self._settings.llm_model
            ),
            raw=body if isinstance(body, dict) else {},
        )

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient()
        return self._http


def _safe_error_body(response: httpx.Response) -> str:
    text = (response.text or "").replace("\n", " ").strip()
    return text[:800] if text else "<empty>"


def _message_content(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        # Some models return a list of typed parts.
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
            and part.get("type") in (None, "text", "output_text")
        ]
        return "".join(parts).strip()
    return ""


def _usage_from(body: dict[str, Any], latency_ms: int, fallback_model: str) -> LlmUsage:
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    cost = usage.get("cost")
    cost_usd: Decimal | None = None
    if isinstance(cost, int | float | str):
        try:
            cost_usd = Decimal(str(cost))
        except Exception:
            cost_usd = None

    model = body.get("model")
    return LlmUsage(
        prompt_tokens=_as_int(usage.get("prompt_tokens")),
        completion_tokens=_as_int(usage.get("completion_tokens")),
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        model=model if isinstance(model, str) else fallback_model,
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a model response, tolerating a fenced ```json block."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = [line for line in lines[1:] if not line.strip().startswith("```")]
        text = "\n".join(inner).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("llm response is not valid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError("llm response is not a JSON object")
    return parsed
