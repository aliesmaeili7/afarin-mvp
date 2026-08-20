import logging
from typing import Protocol

import httpx

from app.core import messages
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.services.storage import paths
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """
    Object storage, kept behind an interface so nothing in the service layer
    knows it is talking to Supabase (spec §23).
    """

    async def upload(
        self, ref: StorageRef, content: bytes, content_type: str
    ) -> None: ...

    async def download(self, ref: StorageRef) -> bytes | None: ...

    async def remove(self, ref: StorageRef) -> None: ...

    async def sign(self, ref: StorageRef, ttl_seconds: int) -> str | None: ...

    async def ensure_bucket(self, bucket: str) -> None: ...


class SupabaseStorage:
    """
    Talks to the Supabase Storage REST API with the service-role key.

    That key lives only here, on the server. The frontend never receives it and
    never contacts storage directly; it only ever holds a short-lived signed URL
    (spec §27).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base = f"{self._settings.supabase_url.rstrip('/')}/storage/v1"

    def _headers(self) -> dict[str, str]:
        key = self._settings.supabase_service_role_key
        return {"Authorization": f"Bearer {key}", "apikey": key}

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers(), timeout=30.0)

    async def ensure_bucket(self, bucket: str) -> None:
        async with await self._client() as client:
            existing = await client.get(f"{self._base}/bucket/{bucket}")
            if existing.status_code == 200:
                return
            created = await client.post(
                f"{self._base}/bucket",
                json={"name": bucket, "id": bucket, "public": False},
            )
            if created.status_code not in (200, 201) and "already" not in created.text:
                raise RuntimeError(f"could not create bucket {bucket}: {created.text}")

    async def upload(self, ref: StorageRef, content: bytes, content_type: str) -> None:
        async with await self._client() as client:
            response = await client.post(
                f"{self._base}/object/{ref.bucket}/{ref.key}",
                content=content,
                headers={"content-type": content_type, "x-upsert": "true"},
            )
        if response.status_code not in (200, 201):
            logger.error(
                "storage upload failed: %s %s", response.status_code, response.text
            )
            raise ApiError("upload_failed", messages.UPLOAD_FAILED)

    async def download(self, ref: StorageRef) -> bytes | None:
        async with await self._client() as client:
            response = await client.get(f"{self._base}/object/{ref.bucket}/{ref.key}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.warning(
                "storage download failed: %s %s", response.status_code, response.text
            )
            return None
        return response.content

    async def remove(self, ref: StorageRef) -> None:
        async with await self._client() as client:
            response = await client.delete(
                f"{self._base}/object/{ref.bucket}/{ref.key}"
            )
        # A missing object is not an error: deleting an image the seller already
        # removed should still leave them with a working screen.
        if response.status_code not in (200, 204, 404):
            logger.warning(
                "storage delete failed: %s %s", response.status_code, response.text
            )

    async def sign(self, ref: StorageRef, ttl_seconds: int) -> str | None:
        async with await self._client() as client:
            response = await client.post(
                f"{self._base}/object/sign/{ref.bucket}/{ref.key}",
                json={"expiresIn": ttl_seconds},
            )
        if response.status_code != 200:
            logger.warning(
                "storage sign failed: %s %s", response.status_code, response.text
            )
            return None
        signed = response.json().get("signedURL") or response.json().get("signedUrl")
        if not signed:
            return None
        return f"{self._settings.supabase_url.rstrip('/')}/storage/v1{signed}"


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = SupabaseStorage()
    return _backend


def set_storage(backend: StorageBackend | None) -> None:
    """Test seam. Production never calls this."""
    global _backend
    _backend = backend


async def resolve_paths(
    storage_paths: list[str], ttl_seconds: int | None = None
) -> dict[str, str | None]:
    """
    Turns opaque storage paths into displayable URLs.

    `public://` assets ship with the frontend and resolve to a static path;
    everything else becomes a short-lived signed URL.
    """
    settings = get_settings()
    ttl = ttl_seconds or settings.signed_url_ttl_seconds
    backend = get_storage()

    resolved: dict[str, str | None] = {}
    for path in storage_paths:
        if paths.is_public(path):
            resolved[path] = f"/{path[len(paths.PUBLIC_PREFIX) :]}"
            continue
        ref = paths.parse(path)
        resolved[path] = await backend.sign(ref, ttl) if ref else None
    return resolved
