"""Phase C chat turn: routing, hint bypass, skills, retry, isolation."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.services.orchestrator.provider import reset_stub_calls, stub_call_count
from app.services.orchestrator.skills.education import EducationSkill
from app.services.orchestrator.skills.registry import _SKILLS
from tests.conftest import auth_header, png_bytes


def _product_png() -> bytes:
    return png_bytes(320, 400)


async def test_explicit_education_hint_skips_orchestrator(
    client: AsyncClient,
) -> None:
    reset_stub_calls()
    user = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
            "language": "fa",
            "action_hint": "education",
        },
        headers=auth_header(user),
    )
    assert created.status_code == 200, created.text
    assert stub_call_count() == 0
    body = created.json()
    roles = [item["role"] for item in body["messages"]]
    assert roles[0] == "user"
    assert "assistant" in roles
    artifacts = body["artifacts"]
    assert artifacts
    assert artifacts[0]["status"] == "ready"
    assert artifacts[0]["storage_path"]
    assert artifacts[0]["metadata_json"]["skill"] == "education"
    assert artifacts[0]["storage_path"].startswith("supabase://")
    assert "/education/" in artifacts[0]["storage_path"]


async def test_explicit_hint_keeps_independent_artifact_language(
    client: AsyncClient,
) -> None:
    reset_stub_calls()
    user = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه پوستر آموزشی بساز ولی متنش انگلیسی باشه",
            "language": "fa",
            "action_hint": "education",
        },
        headers=auth_header(user),
    )
    assert created.status_code == 200, created.text
    assert stub_call_count() == 0
    assistant = next(
        item for item in created.json()["messages"] if item["role"] == "assistant"
    )
    assert assistant["language"] == "fa"
    assert assistant["metadata_json"]["artifact_language"] == "en"


async def test_general_chat_does_not_create_an_artifact(client: AsyncClient) -> None:
    reset_stub_calls()
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام، چطوری؟", "language": "fa"},
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200
    assert stub_call_count() == 1
    body = created.json()
    assert [item["role"] for item in body["messages"]] == ["user", "assistant"]
    assert body["artifacts"] == []
    assistant = body["messages"][1]
    assert assistant["metadata_json"]["route"] == "general_chat"


async def test_unsupported_route(client: AsyncClient) -> None:
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "یه آهنگ بساز", "language": "fa"},
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200
    assistant = next(
        item for item in created.json()["messages"] if item["role"] == "assistant"
    )
    assert assistant["metadata_json"]["route"] == "unsupported"
    assert created.json()["artifacts"] == []


async def test_advertising_without_image_clarifies(client: AsyncClient) -> None:
    reset_stub_calls()
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه تبلیغ از این کفش بساز",
            "language": "fa",
            "action_hint": "advertising",
        },
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200, created.text
    assert stub_call_count() == 0
    assistant = next(
        item for item in created.json()["messages"] if item["role"] == "assistant"
    )
    assert assistant["metadata_json"]["route"] == "clarify"
    assert created.json()["artifacts"] == []


async def test_advertising_with_product_image(client: AsyncClient, storage) -> None:
    user = uuid.uuid4()
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
        headers=auth_header(user),
    )
    assert created.status_code == 200, created.text
    artifacts = created.json()["artifacts"]
    assert artifacts
    assert artifacts[0]["status"] == "ready"
    assert artifacts[0]["aspect_ratio"] == "4:5"
    assert artifacts[0]["metadata_json"]["skill"] == "advertising"
    assert "/campaigns/" in artifacts[0]["storage_path"]


async def test_general_image_stores_under_chat(client: AsyncClient) -> None:
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه تصویر از یک فنجان چای بساز",
            "language": "fa",
            "action_hint": "general_image",
        },
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200, created.text
    artifact = created.json()["artifacts"][0]
    assert artifact["status"] == "ready"
    assert "/chat/" in artifact["storage_path"]
    assert "/artifacts/" in artifact["storage_path"]


async def test_owned_reference_persists_on_follow_up(client: AsyncClient) -> None:
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
    assert created.status_code == 200, created.text
    artifact_id = created.json()["artifacts"][0]["id"]
    conversation_id = created.json()["id"]
    follow = await client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        json={
            "content": "از روی همین یه نسخه گرم‌تر بساز",
            "language": "fa",
            "reference_artifact_ids": [artifact_id],
        },
        headers=headers,
    )
    assert follow.status_code == 200, follow.text
    users = [item for item in follow.json()["messages"] if item["role"] == "user"]
    assert users[-1]["metadata_json"]["reference_artifact_ids"] == [artifact_id]


async def test_busy_conflict_while_generating(client: AsyncClient) -> None:
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=headers,
    )
    conversation_id = created.json()["id"]

    from app.db.models import ChatArtifact, ChatMessage
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        assistant = ChatMessage(
            conversation_id=uuid.UUID(conversation_id),
            role="assistant",
            content="",
            language="fa",
            metadata_json={"status": "generating", "route": "education"},
        )
        session.add(assistant)
        await session.flush()
        session.add(
            ChatArtifact(
                conversation_id=uuid.UUID(conversation_id),
                message_id=assistant.id,
                artifact_type="image",
                status="generating",
            )
        )
        await session.commit()

    blocked = await client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        json={"content": "بازم بساز", "language": "fa"},
        headers=headers,
    )
    assert blocked.status_code == 409


async def test_failed_skill_is_retryable(client: AsyncClient, monkeypatch) -> None:
    async def boom(_session, _context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(_SKILLS["education"], "execute", boom)
    user = uuid.uuid4()
    headers = auth_header(user)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه پست آموزشی درباره کسر بساز",
            "language": "fa",
            "action_hint": "education",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    assistant = next(
        item for item in created.json()["messages"] if item["role"] == "assistant"
    )
    assert assistant["metadata_json"]["failed"] is True
    assert assistant["metadata_json"]["retryable"] is True
    artifact = created.json()["artifacts"][0]
    assert artifact["status"] == "failed"
    users = [item for item in created.json()["messages"] if item["role"] == "user"]
    assert len(users) == 1

    async def succeed(session, context):
        return await EducationSkill().execute(session, context)

    monkeypatch.setattr(_SKILLS["education"], "execute", succeed)
    retried = await client.post(
        f"/api/chat/conversations/{created.json()['id']}/messages/{assistant['id']}/retry",
        headers=headers,
    )
    assert retried.status_code == 200, retried.text
    users_after = [item for item in retried.json()["messages"] if item["role"] == "user"]
    assert len(users_after) == 1
    ready = [item for item in retried.json()["artifacts"] if item["status"] == "ready"]
    assert ready


async def test_retry_is_owner_scoped(client: AsyncClient, monkeypatch) -> None:
    async def boom(_session, _context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(_SKILLS["education"], "execute", boom)
    owner = uuid.uuid4()
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه پست آموزشی بساز",
            "language": "fa",
            "action_hint": "education",
        },
        headers=auth_header(owner),
    )
    assistant_id = next(
        item["id"]
        for item in created.json()["messages"]
        if item["role"] == "assistant"
    )
    conversation_id = created.json()["id"]
    stranger = await client.post(
        f"/api/chat/conversations/{conversation_id}/messages/{assistant_id}/retry",
        headers=auth_header(uuid.uuid4()),
    )
    assert stranger.status_code == 404
    missing = await client.post(
        f"/api/chat/conversations/{uuid.uuid4()}/messages/{assistant_id}/retry",
        headers=auth_header(owner),
    )
    assert missing.status_code == 404


async def test_delete_conversation_keeps_campaign_storage(
    client: AsyncClient, storage
) -> None:
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
    conversation_id = created.json()["id"]
    campaign_keys = [key for key in storage.objects if "/campaigns/" in key]
    chat_keys = [key for key in storage.objects if "/chat/" in key]
    assert campaign_keys
    assert chat_keys
    deleted = await client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert deleted.status_code == 204
    assert [key for key in storage.objects if "/chat/" in key] == []
    assert [key for key in storage.objects if "/campaigns/" in key]


def _assistant(body: dict) -> dict:
    return next(item for item in body["messages"] if item["role"] == "assistant")


async def test_explicit_education_hits_generating_image_at_provider(
    client: AsyncClient,
) -> None:
    from sqlalchemy import select

    from app.db.models import ChatMessage
    from app.db.session import get_sessionmaker
    from app.providers.image import set_image_provider
    from app.providers.image.stub import StubImageProvider

    seen: list[tuple[str | None, str | None]] = []

    class Spy(StubImageProvider):
        async def generate(self, request):
            async with get_sessionmaker()() as session:
                row = await session.scalar(
                    select(ChatMessage)
                    .where(ChatMessage.role == "assistant")
                    .order_by(ChatMessage.created_at.desc())
                )
                meta = row.metadata_json if row is not None else {}
                seen.append((meta.get("activity_phase"), meta.get("route")))
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        reset_stub_calls()
        created = await client.post(
            "/api/chat/conversations",
            json={
                "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
                "language": "fa",
                "action_hint": "education",
            },
            headers=auth_header(uuid.uuid4()),
        )
    finally:
        set_image_provider(None)
    assert created.status_code == 200, created.text
    assert stub_call_count() == 0
    assert seen
    assert seen[0] == ("generating_image", "education")
    assistant = _assistant(created.json())
    assert assistant["metadata_json"]["status"] == "ready"
    assert "activity_phase" not in assistant["metadata_json"]


async def test_explicit_advertising_generating_image_at_provider(
    client: AsyncClient,
) -> None:
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
            return await super().generate(request)

    set_image_provider(Spy())
    try:
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
            headers=auth_header(uuid.uuid4()),
        )
    finally:
        set_image_provider(None)
    assert created.status_code == 200, created.text
    assert seen
    assert seen[0] == "generating_image"
    assistant = _assistant(created.json())
    assert assistant["metadata_json"]["route"] == "advertising"
    assert assistant["metadata_json"]["status"] == "ready"
    assert "activity_phase" not in assistant["metadata_json"]


async def test_general_image_generating_image_at_provider(client: AsyncClient) -> None:
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
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        created = await client.post(
            "/api/chat/conversations",
            json={
                "content": "یه تصویر از یک فنجان چای بساز",
                "language": "fa",
                "action_hint": "general_image",
            },
            headers=auth_header(uuid.uuid4()),
        )
    finally:
        set_image_provider(None)
    assert created.status_code == 200, created.text
    assert seen[0] == "generating_image"
    assistant = _assistant(created.json())
    assert assistant["metadata_json"]["route"] == "general_image"
    assert "activity_phase" not in assistant["metadata_json"]


async def test_unhinted_education_runs_orchestrator_then_image_phase(
    client: AsyncClient,
) -> None:
    from sqlalchemy import select

    from app.db.models import ChatMessage
    from app.db.session import get_sessionmaker
    from app.providers.image import set_image_provider
    from app.providers.image.stub import StubImageProvider

    seen: list[tuple[str | None, str | None]] = []

    class Spy(StubImageProvider):
        async def generate(self, request):
            async with get_sessionmaker()() as session:
                row = await session.scalar(
                    select(ChatMessage)
                    .where(ChatMessage.role == "assistant")
                    .order_by(ChatMessage.created_at.desc())
                )
                meta = row.metadata_json if row is not None else {}
                seen.append((meta.get("activity_phase"), meta.get("route")))
            return await super().generate(request)

    set_image_provider(Spy())
    try:
        reset_stub_calls()
        created = await client.post(
            "/api/chat/conversations",
            json={
                "content": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
                "language": "fa",
            },
            headers=auth_header(uuid.uuid4()),
        )
    finally:
        set_image_provider(None)
    assert created.status_code == 200, created.text
    assert stub_call_count() == 1
    assert seen[0] == ("generating_image", "education")
    assert _assistant(created.json())["metadata_json"]["route"] == "education"


async def test_general_chat_has_no_activity_phase(client: AsyncClient) -> None:
    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام، چطوری؟", "language": "fa"},
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200
    assistant = _assistant(created.json())
    assert assistant["metadata_json"]["route"] == "general_chat"
    assert "activity_phase" not in assistant["metadata_json"]
    assert created.json()["artifacts"] == []


async def test_failed_skill_clears_activity_phase(
    client: AsyncClient, monkeypatch
) -> None:
    async def boom(_session, _context):
        raise RuntimeError("provider down")

    monkeypatch.setattr(_SKILLS["education"], "execute", boom)
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه پست آموزشی درباره کسر بساز",
            "language": "fa",
            "action_hint": "education",
        },
        headers=auth_header(uuid.uuid4()),
    )
    assistant = _assistant(created.json())
    assert assistant["metadata_json"]["status"] == "failed"
    assert "activity_phase" not in assistant["metadata_json"]


async def test_activity_phase_failure_does_not_fail_generation(
    client: AsyncClient, monkeypatch
) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("activity db down")

    monkeypatch.setattr(
        "app.services.orchestrator.skills.education.set_activity_phase", boom
    )
    monkeypatch.setattr(
        "app.services.orchestrator.skills.general_image.set_activity_phase", boom
    )
    created = await client.post(
        "/api/chat/conversations",
        json={
            "content": "یه پست آموزشی درباره کسر بساز",
            "language": "fa",
            "action_hint": "education",
        },
        headers=auth_header(uuid.uuid4()),
    )
    assert created.status_code == 200, created.text
    assert created.json()["artifacts"][0]["status"] == "ready"


async def test_set_activity_phase_merges_without_clobbering(
    client: AsyncClient,
) -> None:
    from sqlalchemy import type_coerce, update
    from sqlalchemy.dialects.postgresql import JSONB

    from app.db.models import ChatMessage
    from app.db.session import get_sessionmaker
    from app.services.orchestrator.activity import set_activity_phase

    created = await client.post(
        "/api/chat/conversations",
        json={"content": "سلام", "language": "fa"},
        headers=auth_header(uuid.uuid4()),
    )
    conversation_id = created.json()["id"]
    async with get_sessionmaker()() as session:
        assistant = ChatMessage(
            conversation_id=uuid.UUID(conversation_id),
            role="assistant",
            content="",
            language="fa",
            metadata_json={
                "status": "generating",
                "route": "education",
                "campaign_id": "keep-me",
                "orchestrator_called": False,
            },
        )
        session.add(assistant)
        await session.commit()
        assistant_id = assistant.id

    async with get_sessionmaker()() as session:
        await session.execute(
            update(ChatMessage)
            .where(ChatMessage.id == assistant_id)
            .values(
                metadata_json=ChatMessage.metadata_json.op("||")(
                    type_coerce({"educational_post_id": "later"}, JSONB)
                )
            )
        )
        await session.commit()

    await set_activity_phase(assistant_id, "generating_image")
    async with get_sessionmaker()() as session:
        row = await session.get(ChatMessage, assistant_id)
        assert row is not None
        assert row.metadata_json["campaign_id"] == "keep-me"
        assert row.metadata_json["educational_post_id"] == "later"
        assert row.metadata_json["orchestrator_called"] is False
        assert row.metadata_json["activity_phase"] == "generating_image"
        assert row.metadata_json["route"] == "education"
