"""OpenRouter Image API contract: 400s are parsed, recorded, and not retried."""

import json
from uuid import UUID, uuid4

import httpx
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import GenerationJob
from app.db.session import get_sessionmaker
from app.providers.image import set_image_provider
from app.providers.image.base import ImageApiError, ImageRequest
from app.providers.image.openrouter.client import OpenRouterImageClient
from app.providers.image.openrouter.provider import OpenRouterImageProvider
from app.providers.llm import set_content_provider
from app.providers.llm.openrouter.provider import OpenRouterContentProvider
from tests.conftest import auth_header
from tests.fakes import FakeLlmClient, copy_package
from tests.test_visuals import _generate, _ready_campaign

PIXEL_ERROR = (
    "bytedance-seed/seedream-4.5 requires at least 3,686,400 output pixels; "
    'size "820x1024" is 839,680. Use a larger resolution such as "2K", '
    "or omit resolution."
)


def _settings(**overrides: object) -> Settings:
    values: dict = {
        "image_provider": "openrouter",
        "openrouter_api_key": "sk-test-secret-key",
        "image_model": "bytedance-seed/seedream-4.5",
        "image_resolution": "2K",
        "llm_base_url": "https://openrouter.test/api/v1",
        "image_max_retries": 2,
        "image_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings(**values)


def _capabilities() -> dict:
    return {
        "data": [
            {
                "id": "bytedance-seed/seedream-4.5",
                "supported_parameters": {
                    "aspect_ratio": {
                        "type": "string",
                        "values": ["1:1", "4:5", "9:16", "16:9"],
                    },
                    "resolution": {"type": "string", "values": ["1K", "2K", "4K"]},
                    "seed": {"type": "boolean"},
                },
            }
        ]
    }


async def test_400_is_parsed_and_not_retried() -> None:
    posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        if request.url.path.endswith("/images/models"):
            return httpx.Response(200, json=_capabilities())
        posts += 1
        assert b"sk-test" not in request.content
        body = json.loads(request.content)
        assert body["model"] == "bytedance-seed/seedream-4.5"
        assert body["aspect_ratio"] in {"4:5", "9:16"}
        assert body["resolution"] == "2K"
        assert "output_format" not in body
        assert "seed" not in body
        return httpx.Response(
            400,
            json={"error": {"code": "bad_request", "message": PIXEL_ERROR}},
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenRouterImageClient(_settings(), http=http)

    try:
        await client.generate(ImageRequest(prompt="empty studio", aspect_ratio="4:5"))
    except ImageApiError as error:
        assert error.status_code == 400
        assert error.retryable is False
        assert "3,686,400" in error.provider_message
        assert "sk-test" not in error.provider_message
        assert "resolution" in error.payload_keys
    else:
        raise AssertionError("expected ImageApiError")
    assert posts == 1


async def test_429_is_retried_then_succeeds() -> None:
    posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        if request.url.path.endswith("/images/models"):
            return httpx.Response(200, json=_capabilities())
        posts += 1
        if posts == 1:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "b64_json": (
                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
                            "nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
                        )
                    }
                ]
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenRouterImageClient(_settings(), http=http)
    result = await client.generate(
        ImageRequest(prompt="empty studio", aspect_ratio="9:16")
    )
    assert posts == 2
    assert result.content.startswith(b"\x89PNG")


async def test_payload_omits_1k_when_discovery_fails() -> None:
    recorded: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images/models"):
            return httpx.Response(500, json={"error": "nope"})
        recorded["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"b64_json": "aGVsbG8="}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenRouterImageClient(_settings(image_resolution="1K"), http=http)
    await client.generate(ImageRequest(prompt="x", aspect_ratio="4:5", resolution="1K"))
    assert recorded["body"]["aspect_ratio"] == "4:5"
    assert "resolution" not in recorded["body"]
    assert "output_format" not in recorded["body"]


async def test_references_are_image_url_objects() -> None:
    recorded: dict = {}
    jpeg = b"\xff\xd8\xff" + b"x" * 12

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images/models"):
            return httpx.Response(200, json=_capabilities())
        recorded["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"b64_json": "aGVsbG8="}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenRouterImageClient(_settings(), http=http)
    await client.generate(
        ImageRequest(prompt="hero", aspect_ratio="4:5", references=(jpeg,))
    )
    refs = recorded["body"]["input_references"]
    assert isinstance(refs[0], dict)
    assert refs[0]["type"] == "image_url"
    assert refs[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


async def test_campaign_job_records_openrouter_400(
    client: AsyncClient, storage
) -> None:
    posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        if request.url.path.endswith("/images/models"):
            return httpx.Response(200, json=_capabilities())
        posts += 1
        return httpx.Response(
            400,
            json={"error": {"code": "bad_request", "message": PIXEL_ERROR}},
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = _settings()
    set_image_provider(
        OpenRouterImageProvider(OpenRouterImageClient(settings, http=http), settings)
    )
    set_content_provider(
        OpenRouterContentProvider(
            FakeLlmClient([copy_package()]),
            Settings(content_provider="openrouter", openrouter_api_key="sk-test"),
        )
    )

    headers = auth_header(uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "partial_failed"
    assert posts == 2

    async with get_sessionmaker()() as session:
        job = await session.scalar(
            select(GenerationJob).where(
                GenerationJob.campaign_id == UUID(campaign_id),
                GenerationJob.job_type == "image_generation",
            )
        )
    assert job is not None
    assert job.status == "failed"
    errors = job.output_json.get("image_errors") or []
    assert errors
    assert errors[0]["http_status"] == 400
    assert errors[0]["retryable"] is False
    assert "3,686,400" in errors[0]["provider_message"]
    assert "sk-test" not in json.dumps(job.output_json)
    assert posts == 2
