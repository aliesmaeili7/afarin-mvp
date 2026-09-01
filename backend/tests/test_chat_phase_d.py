"""Phase D: conversational image edit, references, lineage, advertising product reuse."""

from __future__ import annotations

import io
import uuid

from httpx import AsyncClient
from PIL import Image

from app.services.orchestrator.provider import reset_stub_calls, stub_call_count
from app.services.orchestrator.skills.registry import _SKILLS
from tests.conftest import auth_header, png_bytes


def _product_png() -> bytes:
    return png_bytes(320, 400)


def _image_size(content: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(content)).size


def _assistant(body: dict) -> dict:
    return next(
        item for item in reversed(body["messages"]) if item["role"] == "assistant"
    )


async def _general_image(client: AsyncClient, user: uuid.UUID, text: str = "یه تصویر از یک فنجان چای بساز") -> dict:
    created = await client.post(
        "/api/chat/conversations",
        json={"content": text, "language": "fa", "action_hint": "general_image"},
        headers=auth_header(user),
    )
    assert created.status_code == 200, created.text
    return created.json()


async def test_persian_direct_edit_creates_new_chat_artifact(client: AsyncClient) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await _general_image(client, user)
    source = created["artifacts"][0]
    source_path = source["storage_path"]
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={"content": "روشن‌ترش کن", "language": "fa"},
        headers=headers,
    )
    assert follow.status_code == 200, follow.text
    artifacts = follow.json()["artifacts"]
    assert len(artifacts) == 2
    assert artifacts[0]["id"] == source["id"]
    assert artifacts[0]["storage_path"] == source_path
    edited = artifacts[1]
    assert edited["status"] == "ready"
    assert edited["metadata_json"]["skill"] == "image_edit"
    assert edited["metadata_json"]["source_artifact_ids"] == [source["id"]]
    assert "/chat/" in edited["storage_path"]
    assert "/artifacts/" in edited["storage_path"]
    assert edited["storage_path"] != source_path
    assistant = _assistant(follow.json())
    assert assistant["metadata_json"]["route"] == "image_edit"
    assert assistant["language"] == "fa"


async def test_english_direct_edit(client: AsyncClient) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "Make a simple illustration of a teacup.",
            "language": "en",
            "action_hint": "general_image",
        },
        headers=headers,
    )
    follow = await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages",
        json={"content": "make this brighter", "language": "en"},
        headers=headers,
    )
    assert follow.status_code == 200, follow.text
    assert _assistant(follow.json())["language"] == "en"
    assert follow.json()["artifacts"][-1]["metadata_json"]["skill"] == "image_edit"


async def test_no_image_edit_clarifies_without_paid_call(
    client: AsyncClient, monkeypatch
) -> None:
    called = {"n": 0}

    async def boom(_session, _context):
        called["n"] += 1
        raise AssertionError("image_edit should not run")

    monkeypatch.setattr(_SKILLS["image_edit"], "execute", boom)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "روشن‌ترش کن", "language": "fa"},
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200, created.text
    assert created.json()["artifacts"] == []
    assert _assistant(created.json())["metadata_json"]["route"] == "clarify"
    assert called["n"] == 0


async def test_ambiguous_images_clarify(client: AsyncClient, monkeypatch) -> None:
    called = {"n": 0}

    async def boom(_session, _context):
        called["n"] += 1
        raise AssertionError("should clarify")

    monkeypatch.setattr(_SKILLS["image_edit"], "execute", boom)
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await _general_image(client, user)
    second = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={
            "content": "یه تصویر از یک گل بساز",
            "language": "fa",
            "action_hint": "general_image",
        },
        headers=headers,
    )
    assert len(second.json()["artifacts"]) == 2
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={"content": "روشن‌ترش کن", "language": "fa"},
        headers=headers,
    )
    assert follow.status_code == 200, follow.text
    assert _assistant(follow.json())["metadata_json"]["route"] == "clarify"
    assert called["n"] == 0
    assert len(follow.json()["artifacts"]) == 2


async def test_explicit_reference_picks_the_older_image(client: AsyncClient) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await _general_image(client, user)
    first_id = created["artifacts"][0]["id"]
    await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={
            "content": "یه تصویر از یک گل بساز",
            "language": "fa",
            "action_hint": "general_image",
        },
        headers=headers,
    )
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={
            "content": "روشن‌ترش کن",
            "language": "fa",
            "reference_artifact_ids": [first_id],
        },
        headers=headers,
    )
    edited = follow.json()["artifacts"][-1]
    assert edited["metadata_json"]["source_artifact_ids"] == [first_id]


async def test_foreign_reference_does_not_edit(client: AsyncClient) -> None:
    owner = uuid.uuid4()
    owned = await _general_image(client, owner)
    artifact_id = owned["artifacts"][0]["id"]
    stranger = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=auth_header(stranger),
    )
    follow = await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages",
        json={
            "content": "روشن‌ترش کن",
            "language": "fa",
            "reference_artifact_ids": [artifact_id],
        },
        headers=auth_header(stranger),
    )
    assert follow.status_code == 200, follow.text
    assert _assistant(follow.json())["metadata_json"]["route"] == "clarify"
    assert all(item["id"] != artifact_id for item in follow.json()["artifacts"])


async def test_failed_artifact_is_not_an_edit_source(
    client: AsyncClient, monkeypatch
) -> None:
    async def boom(_session, _context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(_SKILLS["general_image"], "execute", boom)
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه تصویر از یک فنجان چای بساز",
            "language": "fa",
            "action_hint": "general_image",
        },
        headers=headers,
    )
    failed_id = created.json()["artifacts"][0]["id"]
    follow = await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages",
        json={
            "content": "روشن‌ترش کن",
            "language": "fa",
            "reference_artifact_ids": [failed_id],
        },
        headers=headers,
    )
    assert _assistant(follow.json())["metadata_json"]["route"] == "clarify"


async def test_quoted_text_is_passed_to_the_image_provider(client: AsyncClient) -> None:
    from app.providers.image import set_image_provider
    from app.providers.image.stub import StubImageProvider

    seen: list[str] = []

    class Spy(StubImageProvider):
        async def generate(self, request):
            seen.append(request.prompt)
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        user = uuid.uuid4()
        created = await _general_image(client, user)
        await client.post(
            f"/api/chat/conversations/{created['id']}/messages",
            json={
                "content": "تیتر رو بکن «ماموریت کسرها»",
                "language": "fa",
            },
            headers=auth_header(user),
        )
    finally:
        set_image_provider(None)
    assert seen
    assert "ماموریت کسرها" in seen[-1]
    assert "transliterate" in seen[-1].lower() or "exactly" in seen[-1].lower()


async def test_story_reframe_persists_9_16(client: AsyncClient) -> None:
    user = uuid.uuid4()
    created = await _general_image(client, user)
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={"content": "همین رو استوری کن", "language": "fa"},
        headers=auth_header(user),
    )
    assert follow.json()["artifacts"][-1]["aspect_ratio"] == "9:16"


async def test_preparing_edit_then_generating_image(client: AsyncClient) -> None:
    from sqlalchemy import select

    from app.db.models import ChatMessage
    from app.db.session import get_sessionmaker
    from app.providers.image import set_image_provider
    from app.providers.image.stub import StubImageProvider

    seen: list[str | None] = []

    class Spy(StubImageProvider):
        async def generate(self, request):
            async with get_sessionmaker()() as session:
                row = await session.scalar(
                    select(ChatMessage)
                    .where(ChatMessage.role == "assistant")
                    .order_by(ChatMessage.created_at.desc())
                )
                seen.append(
                    None if row is None else row.metadata_json.get("activity_phase")
                )
            if len(seen) > 1:
                assert request.references
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        user = uuid.uuid4()
        created = await _general_image(client, user)
        follow = await client.post(
            f"/api/chat/conversations/{created['id']}/messages",
            json={"content": "روشن‌ترش کن", "language": "fa"},
            headers=auth_header(user),
        )
    finally:
        set_image_provider(None)
    assert seen[0] == "generating_image"
    assistant = _assistant(follow.json())
    assert assistant["metadata_json"]["route"] == "image_edit"
    assert "activity_phase" not in assistant["metadata_json"]


async def test_retry_edit_reuses_source_without_new_user_message(
    client: AsyncClient, monkeypatch
) -> None:
    async def boom(_session, _context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(_SKILLS["image_edit"], "execute", boom)
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await _general_image(client, user)
    source_id = created["artifacts"][0]["id"]
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={"content": "روشن‌ترش کن", "language": "fa"},
        headers=headers,
    )
    assistant = _assistant(follow.json())
    users = [item for item in follow.json()["messages"] if item["role"] == "user"]
    assert assistant["metadata_json"]["failed"] is True
    assert assistant["content"]

    from app.services.orchestrator.skills.image_edit import ImageEditSkill

    monkeypatch.setattr(_SKILLS["image_edit"], "execute", ImageEditSkill().execute)
    retried = await client.post(
        f"/api/chat/conversations/{created['id']}/messages/{assistant['id']}/retry",
        headers=headers,
    )
    assert retried.status_code == 200, retried.text
    users_after = [item for item in retried.json()["messages"] if item["role"] == "user"]
    assert len(users_after) == len(users)
    edited = retried.json()["artifacts"][-1]
    assert edited["status"] == "ready"
    assert edited["metadata_json"]["source_artifact_ids"] == [source_id]


async def test_caption_with_reference_stays_general_chat(client: AsyncClient) -> None:
    reset_stub_calls()
    user = uuid.uuid4()
    created = await _general_image(client, user)
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={
            "content": "یه کپشن براش بده",
            "language": "fa",
            "reference_artifact_ids": [created["artifacts"][0]["id"]],
        },
        headers=auth_header(user),
    )
    assert stub_call_count() == 1
    assert follow.json()["artifacts"][-1]["id"] == created["artifacts"][0]["id"]
    assert _assistant(follow.json())["metadata_json"]["route"] == "general_chat"


async def test_education_edit_does_not_mutate_post(client: AsyncClient) -> None:
    from app.db.models import EducationalPost
    from app.db.session import get_sessionmaker

    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
            "language": "fa",
            "action_hint": "education",
        },
        headers=headers,
    )
    post_id = created.json()["artifacts"][0]["metadata_json"]["educational_post_id"]
    async with get_sessionmaker()() as session:
        post = await session.get(EducationalPost, uuid.UUID(post_id))
        original_path = post.image_storage_path if post is not None else None
    follow = await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages",
        json={"content": "صندوق گنج رو حذف کن", "language": "fa"},
        headers=headers,
    )
    edited = follow.json()["artifacts"][-1]
    assert edited["metadata_json"]["skill"] == "image_edit"
    assert edited["metadata_json"]["source_domain"] == "education"
    async with get_sessionmaker()() as session:
        post = await session.get(EducationalPost, uuid.UUID(post_id))
        assert post is not None
        assert post.image_storage_path == original_path


async def test_advertising_another_version_reuses_product_photo_not_rendered_ad(
    client: AsyncClient,
) -> None:
    from app.providers.image import set_image_provider
    from app.providers.image.stub import StubImageProvider

    refs: list[tuple[bytes, ...]] = []

    class Spy(StubImageProvider):
        async def generate(self, request):
            refs.append(request.references)
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        user = uuid.uuid4()
        headers = auth_header(user)
        created = await client.post(
            "/api/chat/conversations",
            files={
                "payload": (
                    None,
                    '{"content":"یه تبلیغ از این بساز","language":"fa","action_hint":"advertising"}',
                    "application/json",
                ),
                "attachment": ("shoe.png", _product_png(), "image/png"),
            },
            headers=headers,
        )
        assert created.status_code == 200, created.text
        ad_id = created.json()["artifacts"][0]["id"]
        follow = await client.post(
            f"/api/chat/conversations/{created.json()['id']}/messages",
            json={
                "content": "یکی دیگه تبلیغ بساز",
                "language": "fa",
                "reference_artifact_ids": [ad_id],
            },
            headers=headers,
        )
        assert follow.status_code == 200, follow.text
        assert _assistant(follow.json())["metadata_json"]["route"] == "advertising"
    finally:
        set_image_provider(None)
    assert refs
    last = refs[-1]
    assert last
    assert _image_size(last[0]) == (320, 400)


async def test_mixed_edit_keeps_reply_language_persian(client: AsyncClient) -> None:
    user = uuid.uuid4()
    created = await _general_image(client, user)
    follow = await client.post(
        f"/api/chat/conversations/{created['id']}/messages",
        json={"content": "تیترش رو انگلیسی کن", "language": "fa"},
        headers=auth_header(user),
    )
    assistant = _assistant(follow.json())
    assert assistant["language"] == "fa"
    assert assistant["metadata_json"].get("artifact_language") == "en"


async def test_current_turn_upload_can_be_edited(client: AsyncClient) -> None:
    user = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        files={
            "payload": (
                None,
                '{"content":"پس‌زمینه رو سفید کن","language":"fa"}',
                "application/json",
            ),
            "attachment": ("photo.png", _product_png(), "image/png"),
        },
        headers=auth_header(user),
    )
    assert created.status_code == 200, created.text
    artifact = created.json()["artifacts"][0]
    assert artifact["metadata_json"]["skill"] == "image_edit"
    assert artifact["metadata_json"]["source_artifact_ids"] == []
    assert "/chat/" in artifact["storage_path"]


async def test_delete_keeps_education_storage_after_edit(
    client: AsyncClient, storage
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
            "language": "fa",
            "action_hint": "education",
        },
        headers=headers,
    )
    await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages",
        json={"content": "روشن‌ترش کن", "language": "fa"},
        headers=headers,
    )
    education_before = [key for key in storage.objects if "/education/" in key]
    assert education_before
    deleted = await client.delete(
        f"/api/chat/conversations/{created.json()['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert [key for key in storage.objects if "/chat/" in key] == []
    assert [key for key in storage.objects if "/education/" in key]
