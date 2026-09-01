"""OpenRouter client and provider behaviour with a fake HTTP/LLM client."""

import json
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from app.content.context import CopyContext
from app.core.config import Settings
from app.core.errors import ApiError
from app.providers.llm.openrouter.client import OpenRouterClient, parse_json_object
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from app.providers.llm.openrouter.schemas import LlmConcepts, strict_schema
from tests.fakes import FakeLlmClient, copy_package, three_concepts


def _ctx() -> CopyContext:
    return CopyContext(
        product_name="زعفران ممتاز قائنات",
        description="یک گرمی",
        price_text="۳۹۹ هزار تومان",
        benefit="عطر قوی",
        brand_name="زعفران آرین",
        audience="هدیه",
        objective="sell_product",
        style="luxury",
        round=0,
    )


def _settings(**overrides: object) -> Settings:
    values: dict = {
        "content_provider": "openrouter",
        "openrouter_api_key": "sk-test",
        "llm_model": "openai/gpt-5-mini",
        "llm_base_url": "https://openrouter.test/api/v1",
        "llm_timeout_seconds": 5,
        "llm_max_retries": 2,
    }
    values.update(overrides)
    return Settings(**values)


async def test_client_sends_schema_and_maps_usage() -> None:
    recorded: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["headers"] = dict(request.headers)
        recorded["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-5-mini",
                "choices": [{"message": {"content": json.dumps({"ok": True})}}],
                "usage": {
                    "prompt_tokens": 9,
                    "completion_tokens": 3,
                    "cost": 0.0025,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    client = OpenRouterClient(_settings(), http=http)

    result = await client.complete_json(
        messages=[{"role": "user", "content": "hi"}],
        schema_name="probe",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert recorded["url"].endswith("/chat/completions")
    assert recorded["headers"]["authorization"] == "Bearer sk-test"
    assert recorded["body"]["response_format"]["json_schema"]["strict"] is True
    assert recorded["body"]["max_tokens"] == 16384
    assert recorded["body"]["usage"] == {"include": True}
    assert result.usage.prompt_tokens == 9
    assert result.usage.completion_tokens == 3
    assert result.usage.cost_usd == Decimal("0.0025")
    assert parse_json_object(result.content) == {"ok": True}


def test_parse_json_object_tolerates_wrappers_and_trailing_commas() -> None:
    assert parse_json_object('```json\n{"ok": true}\n```') == {"ok": True}
    assert parse_json_object('prefix {"ok": true, } trailing') == {"ok": True}
    wrapped = json.dumps(json.dumps({"ok": True}))
    assert parse_json_object(wrapped) == {"ok": True}


async def test_parsed_message_field_is_used_when_content_empty() -> None:
    recorded: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        recorded["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-5-mini",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "", "parsed": {"ok": True}},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0},
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenRouterClient(_settings(), http=http)
    result = await client.complete_json(
        messages=[{"role": "user", "content": "hi"}],
        schema_name="probe",
        schema={"type": "object"},
    )
    assert parse_json_object(result.content) == {"ok": True}


async def test_client_timeouts_become_generation_failed() -> None:
    class TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("slow")

    client = OpenRouterClient(
        _settings(), http=httpx.AsyncClient(transport=TimeoutTransport())
    )
    with pytest.raises(ApiError) as caught:
        await client.complete_json(
            messages=[], schema_name="x", schema={"type": "object"}
        )
    assert caught.value.code == "generation_failed"


async def test_empty_key_fails_closed() -> None:
    client = OpenRouterClient(_settings(openrouter_api_key=""))
    with pytest.raises(ApiError) as caught:
        await client.complete_json(
            messages=[], schema_name="x", schema={"type": "object"}
        )
    assert caught.value.code == "generation_failed"


async def test_provider_maps_concepts_and_assigns_background_ids() -> None:
    provider = OpenRouterContentProvider(FakeLlmClient([three_concepts()]), _settings())
    drafts = await provider.build_concepts(_ctx())
    assert len(drafts) == 3
    assert drafts[0].headline_fa.startswith("زعفران ممتاز قائنات")
    assert {draft.background_id for draft in drafts} <= {
        "luxury_night",
        "luxury_velvet",
    }
    assert all("no text" in draft.background_prompt for draft in drafts)
    usage = provider.consume_usage()
    assert usage is not None
    assert usage.prompt_tokens == 11


async def test_copy_package_is_fetched_once() -> None:
    fake = FakeLlmClient([copy_package()])
    provider = OpenRouterContentProvider(fake, _settings())
    ctx = _ctx()
    captions = await provider.build_captions(ctx)
    stories = await provider.build_story_ideas(ctx)
    assert captions.caption_short.startswith("زعفران")
    assert len(stories) == 3
    assert len(fake.calls) == 1


async def test_invalid_output_is_retried_then_accepted() -> None:
    fake = FakeLlmClient([copy_package()])
    fake.invalid_first = True
    provider = OpenRouterContentProvider(fake, _settings())
    captions = await provider.build_captions(_ctx())
    assert captions.caption_short
    assert len(fake.calls) == 2


async def test_invalid_json_is_retried_then_accepted() -> None:
    fake = FakeLlmClient([copy_package()])
    fake.invalid_json_first = True
    provider = OpenRouterContentProvider(fake, _settings())
    captions = await provider.build_captions(_ctx())
    assert captions.caption_short
    assert len(fake.calls) == 2


async def test_invalid_output_fails_after_retries() -> None:
    class AlwaysInvalid(FakeLlmClient):
        async def complete_json(self, **kwargs):
            self.calls.append(kwargs)
            from app.providers.llm.base import LlmUsage
            from app.providers.llm.openrouter.client import CompletionResult

            return CompletionResult(content="{}", usage=LlmUsage(), raw={})

    fake = AlwaysInvalid()
    provider = OpenRouterContentProvider(fake, _settings())
    with pytest.raises(ApiError) as caught:
        await provider.build_concepts(_ctx())
    assert caught.value.code == "generation_failed"
    assert len(fake.calls) == 3


def test_strict_schema_closes_objects() -> None:
    schema = strict_schema(LlmConcepts)
    assert schema["additionalProperties"] is False
    assert "concepts" in schema["required"]


def test_strict_schema_requires_defaulted_fields() -> None:
    """
    OpenRouter strict mode rejects `default` and demands every property in
    `required`, while Pydantic omits defaulted fields from `required`. The
    educational result carries several defaulted fields, so it is the useful
    model to hold that behaviour down.
    """
    from app.providers.education.schemas import LlmEducationalPostResult

    schema = strict_schema(LlmEducationalPostResult)
    dumped = json.dumps(schema)
    assert "default" not in dumped

    assert "language" in schema["required"]
    assert "final_prompt" in schema["required"]
    assert "theme" in schema["required"]
    for field in ("theme_style_notes", "safety_notes"):
        assert field in schema["required"]
    assert "content" not in schema["properties"]
    assert "visual_plan" not in schema["properties"]

    theme = schema["properties"]["theme"]
    assert "secondary_colors" in theme["required"]
    assert "decorative_motifs" in theme["required"]
    assert "mood" in theme["required"]
    assert "lighting" in theme["required"]
    assert "typography" not in theme.get("properties", {})
    assert "font_role" not in theme.get("properties", {})
    assert theme["additionalProperties"] is False


def test_pydantic_rejects_two_concepts() -> None:
    with pytest.raises(ValidationError):
        LlmConcepts.model_validate({"concepts": three_concepts()["concepts"][:2]})
