"""Chat persistence: ownership, lazy create, messages, mutations. No model calls."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import text

from app.db.models import ChatArtifact
from app.db.session import get_sessionmaker
from tests.conftest import auth_header, png_bytes


async def _count(table: str) -> int:
    async with get_sessionmaker()() as session:
        value = await session.scalar(text(f"select count(*) from {table}"))
        return int(value or 0)


def _tiny_png() -> bytes:
    return png_bytes(32, 32)


async def test_list_does_not_create_a_row(client: AsyncClient) -> None:
    user = uuid.uuid4()
    before = await _count("chat_conversations")
    response = await client.get(
        "/api/chat/conversations", headers=auth_header(user)
    )
    assert response.status_code == 200
    assert response.json() == []
    assert await _count("chat_conversations") == before


async def test_anonymous_list_is_empty_and_create_is_forbidden(
    client: AsyncClient,
) -> None:
    listed = await client.get("/api/chat/conversations")
    assert listed.status_code == 200
    assert listed.json() == []

    created = await client.post(
        "/api/chat/conversations", json={"content": "سلام"}
    )
    assert created.status_code == 403
    assert created.json()["code"] == "unauthorized"
    assert await _count("chat_conversations") == 0


async def test_first_send_creates_one_conversation_with_user_message(
    client: AsyncClient,
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
            "language": "fa",
            "action_hint": "education",
            "active_theme": {
                "id": "saved-clay",
                "source": "chat_catalog",
                "name": "خمیری و بازیگوش",
                "style_json": {},
                "swatch": "linear-gradient(135deg, #f6c27a, #f08a5d)",
            },
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["title"].startswith("برای کلاس ششم")
    assert body["language"] == "fa"
    assert body["active_theme"]["id"] == "saved-clay"
    assert body["active_theme"]["name"] == "خمیری و بازیگوش"
    assert "swatch" not in body["active_theme"]
    assert body["active_theme"]["style_json"] == {}
    assert len(body["messages"]) >= 1
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["metadata_json"]["explicit_skill_hint"] == "education"
    assert await _count("chat_conversations") == 1
    assert await _count("chat_messages") >= 1


async def test_second_message_keeps_both_user_turns(
    client: AsyncClient,
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=headers,
    )
    conversation_id = created.json()["id"]
    added = await client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        json={"content": "یک کپشن بنویس", "language": "fa"},
        headers=headers,
    )
    assert added.status_code == 200
    users = [item for item in added.json()["messages"] if item["role"] == "user"]
    assert [item["content"] for item in users] == ["سلام", "یک کپشن بنویس"]


async def test_owner_can_list_get_rename_pin_archive_restore_delete(
    client: AsyncClient,
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "تبلیغ کفش سفید", "language": "fa"},
        headers=headers,
    )
    conversation_id = created.json()["id"]

    listed = await client.get("/api/chat/conversations", headers=headers)
    assert [item["id"] for item in listed.json()] == [conversation_id]

    renamed = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={"title": "کفش"},
        headers=headers,
    )
    assert renamed.json()["title"] == "کفش"

    pinned = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={"pinned": True},
        headers=headers,
    )
    assert pinned.json()["pinned"] is True
    assert pinned.json()["pinned_at"]

    archived = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={"archived": True},
        headers=headers,
    )
    assert archived.json()["archived"] is True
    assert archived.json()["pinned"] is False
    open_list = await client.get("/api/chat/conversations", headers=headers)
    assert open_list.json() == []
    hidden = await client.get(
        "/api/chat/conversations",
        params={"archived": True},
        headers=headers,
    )
    assert [item["id"] for item in hidden.json()] == [conversation_id]

    restored = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={"archived": False},
        headers=headers,
    )
    assert restored.json()["archived"] is False

    deleted = await client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert deleted.status_code == 204
    assert await _count("chat_conversations") == 0
    assert await _count("chat_messages") == 0


async def test_stranger_cannot_see_or_mutate_another_users_chat(
    client: AsyncClient,
) -> None:
    owner = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "خصوصی", "language": "fa"},
        headers=auth_header(owner),
    )
    conversation_id = created.json()["id"]
    stranger = auth_header(uuid.uuid4())

    listed = await client.get("/api/chat/conversations", headers=stranger)
    assert listed.json() == []

    for method, path, kwargs in (
        ("GET", f"/api/chat/conversations/{conversation_id}", {}),
        (
            "PATCH",
            f"/api/chat/conversations/{conversation_id}",
            {"json": {"title": "hack"}},
        ),
        ("DELETE", f"/api/chat/conversations/{conversation_id}", {}),
        (
            "POST",
            f"/api/chat/conversations/{conversation_id}/messages",
            {"json": {"content": "hi"}},
        ),
    ):
        response = await client.request(method, path, headers=stranger, **kwargs)
        assert response.status_code == 404, path
        assert response.json()["message_fa"] == "این گفتگو پیدا نشد."
        assert "خصوصی" not in response.text

    missing = await client.get(
        f"/api/chat/conversations/{uuid.uuid4()}",
        headers=auth_header(owner),
    )
    assert missing.status_code == 404
    assert missing.json()["message_fa"] == "این گفتگو پیدا نشد."


async def test_theme_patch_and_clear(client: AsyncClient) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=headers,
    )
    conversation_id = created.json()["id"]
    assert created.json()["active_theme"] is None

    themed = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={
            "active_theme": {
                "id": "catalog-modern",
                "source": "chat_catalog",
                "name": "Modern",
                "style_json": {"mood": "editorial"},
            }
        },
        headers=headers,
    )
    assert themed.json()["active_theme"]["id"] == "catalog-modern"
    assert themed.json()["active_theme"]["style_json"] == {"mood": "editorial"}

    cleared = await client.patch(
        f"/api/chat/conversations/{conversation_id}",
        json={"active_theme": None},
        headers=headers,
    )
    assert cleared.json()["active_theme"] is None


async def test_search_is_owner_scoped_and_skips_archived(
    client: AsyncClient,
) -> None:
    user = uuid.uuid4()
    other = uuid.uuid4()
    headers = auth_header(user)
    first = await client.post(
        "/api/chat/conversations",
        json={"content": "تبلیغ کفش سفید", "language": "fa"},
        headers=headers,
    )
    second = await client.post(
        "/api/chat/conversations",
        json={"content": "ماموریت ممیز کوچولو", "language": "fa"},
        headers=headers,
    )
    await client.patch(
        f"/api/chat/conversations/{second.json()['id']}",
        json={"archived": True},
        headers=headers,
    )
    await client.post(
        "/api/chat/conversations",
        json={"content": "تبلیغ کفش سفید", "language": "fa"},
        headers=auth_header(other),
    )

    found = await client.get(
        "/api/chat/conversations",
        params={"q": "کفش"},
        headers=headers,
    )
    ids = [item["id"] for item in found.json()]
    assert ids == [first.json()["id"]]


async def test_message_order_and_language_survive_reload(
    client: AsyncClient,
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=headers,
    )
    conversation_id = created.json()["id"]
    await client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        json={"content": "Make this brighter", "language": "en"},
        headers=headers,
    )
    detail = await client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    messages = detail.json()["messages"]
    users = [item for item in messages if item["role"] == "user"]
    assert [item["content"] for item in users] == [
        "سلام",
        "Make this brighter",
    ]
    assert [item["language"] for item in users] == ["fa", "en"]
    assert detail.json()["language"] == "en"


async def test_attachment_upload_is_owner_scoped(
    client: AsyncClient, storage
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        files={
            "payload": (
                None,
                '{"content":"این عکس","language":"fa"}',
                "application/json",
            ),
            "attachment": ("shoe.png", _tiny_png(), "image/png"),
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    user_message = next(
        item for item in created.json()["messages"] if item["role"] == "user"
    )
    attachment = user_message["metadata_json"]["attachment"]
    path = attachment["storage_path"]
    assert path.startswith("supabase://product-images/chat/")
    assert "/attachments/" in path
    assert storage.objects

    resolved = await client.post(
        "/api/assets/resolve", json={"paths": [path]}, headers=headers
    )
    assert resolved.json()[path]
    assert resolved.json()[path].startswith("https://storage.test/")

    stranger = await client.post(
        "/api/assets/resolve",
        json={"paths": [path]},
        headers=auth_header(uuid.uuid4()),
    )
    assert stranger.json() == {path: None}


async def test_delete_removes_storage_objects(
    client: AsyncClient, storage
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        files={
            "payload": (None, '{"content":"عکس","language":"fa"}', "application/json"),
            "attachment": ("a.png", _tiny_png(), "image/png"),
        },
        headers=headers,
    )
    conversation_id = created.json()["id"]
    assert storage.objects
    await client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert storage.objects == {}


async def test_failed_upload_does_not_leave_a_conversation(
    client: AsyncClient, storage, monkeypatch
) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("storage down")

    monkeypatch.setattr(storage, "upload", boom)
    user = uuid.uuid4()
    response = await client.post(
        "/api/chat/conversations",
        files={
            "payload": (None, '{"content":"عکس","language":"fa"}', "application/json"),
            "attachment": ("a.png", _tiny_png(), "image/png"),
        },
        headers=auth_header(user),
    )
    assert response.status_code == 400
    assert await _count("chat_conversations") == 0
    assert storage.objects == {}


async def test_artifact_row_persists_and_is_owner_scoped(
    client: AsyncClient, storage
) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "یه تصویر", "language": "fa"},
        headers=headers,
    )
    conversation_id = uuid.UUID(created.json()["id"])
    message_id = uuid.UUID(
        next(
            item["id"]
            for item in created.json()["messages"]
            if item["role"] == "user"
        )
    )
    path = f"supabase://product-images/chat/{conversation_id}/artifacts/seed.png"
    storage.objects[f"product-images/chat/{conversation_id}/artifacts/seed.png"] = (
        b"fake"
    )

    async with get_sessionmaker()() as session:
        session.add(
            ChatArtifact(
                conversation_id=conversation_id,
                message_id=message_id,
                artifact_type="image",
                storage_path=path,
                status="ready",
                aspect_ratio="1:1",
            )
        )
        await session.commit()

    detail = await client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert detail.json()["artifacts"][0]["storage_path"] == path
    assert detail.json()["artifacts"][0]["artifact_type"] == "image"

    resolved = await client.post(
        "/api/assets/resolve", json={"paths": [path]}, headers=headers
    )
    assert resolved.json()[path]
    stranger = await client.post(
        "/api/assets/resolve",
        json={"paths": [path]},
        headers=auth_header(uuid.uuid4()),
    )
    assert stranger.json() == {path: None}


async def test_empty_payload_does_not_create_a_row(client: AsyncClient) -> None:
    user = uuid.uuid4()
    response = await client.post(
        "/api/chat/conversations",
        json={"content": "   "},
        headers=auth_header(user),
    )
    assert response.status_code == 422
    assert await _count("chat_conversations") == 0
