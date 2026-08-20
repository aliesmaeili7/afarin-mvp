import io
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import text

from app.core import deps, security
from app.core.config import get_settings
from app.db.models import APP_TABLES
from app.db.session import dispose_engine, get_sessionmaker
from app.main import create_app
from app.providers.image import set_image_provider
from app.providers.llm import set_content_provider
from app.services.campaigns.cutout import PassthroughCutout, set_cutout
from app.services.storage import StorageRef, set_storage

# Generation is simulated, and the point of these tests is the persistence, not
# the fourteen seconds of theatre. Every test runs with the delay switched off.
TEST_SETTINGS_ENV = {
    "GENERATION_SIMULATED_MS": "0",
    "GENERATION_QUEUE_MS": "0",
    "DB_NULL_POOL": "true",
    "CONTENT_PROVIDER": "stub",
    "IMAGE_PROVIDER": "stub",
}


class InMemoryStorage:
    """Stands in for Supabase Storage so tests need no network."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def ensure_bucket(self, bucket: str) -> None:
        return None

    async def upload(self, ref: StorageRef, content: bytes, content_type: str) -> None:
        self.objects[f"{ref.bucket}/{ref.key}"] = content

    async def download(self, ref: StorageRef) -> bytes | None:
        return self.objects.get(f"{ref.bucket}/{ref.key}")

    async def remove(self, ref: StorageRef) -> None:
        self.objects.pop(f"{ref.bucket}/{ref.key}", None)

    async def sign(self, ref: StorageRef, ttl_seconds: int) -> str | None:
        key = f"{ref.bucket}/{ref.key}"
        if key not in self.objects:
            return None
        return f"https://storage.test/{key}?token=signed&ttl={ttl_seconds}"


@pytest.fixture(scope="session", autouse=True)
def _configure() -> None:
    for key, value in TEST_SETTINGS_ENV.items():
        os.environ[key] = value
    get_settings.cache_clear()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Paid OpenRouter stays out of the default suite even if a key is in the env."""
    expr = (config.option.markexpr or "").strip()
    if expr == "live":
        return
    skip_live = pytest.mark.skip(reason="optional live test; run with pytest -m live")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
async def _fresh_engine() -> AsyncIterator[None]:
    """Each test gets its own event loop, so it gets its own engine."""
    yield
    await dispose_engine()
    set_content_provider(None)
    set_image_provider(None)
    set_cutout(None)


@pytest.fixture
def storage() -> InMemoryStorage:
    backend = InMemoryStorage()
    set_storage(backend)
    set_cutout(PassthroughCutout())
    yield backend
    set_storage(None)
    set_cutout(None)


@pytest.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    # DELETE rather than TRUNCATE on purpose: afarin_app holds only DML rights,
    # so a TRUNCATE here would pass tests that production could never run.
    # Reverse order walks children before parents.
    async with get_sessionmaker()() as session:
        for table in reversed(APP_TABLES):
            await session.execute(text(f"delete from {table}"))
        await session.commit()
    yield


@pytest.fixture(autouse=True)
def _fake_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Accepts `Bearer test:<uuid>:<email>` in place of a real Supabase JWT.

    Signature verification itself is covered separately in test_security.py; the
    flow tests care about what happens after a token is trusted.
    """

    def verify(token: str) -> security.AuthenticatedUser:
        if not token.startswith("test:"):
            raise security.InvalidToken("not a test token")
        _, user_id, email = token.split(":", 2)
        return security.AuthenticatedUser(user_id=user_id, email=email or None)

    monkeypatch.setattr(deps, "verify_access_token", verify)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://api.test"
    ) as http_client:
        yield http_client


def auth_header(
    user_id: uuid.UUID, email: str = "seller@example.com"
) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{user_id}:{email}"}


def png_bytes(width: int = 64, height: int = 64) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 120, 60)).save(buffer, format="PNG")
    return buffer.getvalue()
