"""
Chat persistence services. User turns live here; generation lives in orchestrator.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core import messages
from app.core.config import Settings
from app.core.errors import invalid
from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.schemas.chat import (
    CHAT_LIST_LIMIT_DEFAULT,
    CHAT_MESSAGE_LIMIT_DEFAULT,
    MAX_MESSAGE_CHARS,
    TITLE_DISPLAY_CHARS,
    ConversationPatchIn,
    CreateMessageIn,
    ThemeSnapshot,
)
from app.services.storage import (
    StorageRef,
    get_storage,
    parse,
    validate_upload,
)
from app.services.storage.images import guard_storage_failure
from app.services.storage.paths import chat_attachment_key

logger = logging.getLogger(__name__)


def title_from_content(content: str, language: str | None) -> str:
    trimmed = " ".join(content.split())
    if not trimmed:
        return "New chat" if language == "en" else "گفتگوی جدید"
    if len(trimmed) > TITLE_DISPLAY_CHARS:
        return f"{trimmed[:TITLE_DISPLAY_CHARS]}…"
    return trimmed


def snapshot_dict(theme: ThemeSnapshot | None) -> dict[str, Any] | None:
    if theme is None:
        return None
    return theme.model_dump()


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _message_metadata(
    body: CreateMessageIn, attachment: dict[str, Any] | None
) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if body.action_hint:
        meta["explicit_skill_hint"] = body.action_hint
    if body.reference_artifact_ids:
        meta["reference_artifact_ids"] = [
            str(item) for item in body.reference_artifact_ids
        ]
    if attachment:
        meta["attachment"] = attachment
    return meta


async def store_chat_attachment(
    *,
    conversation_id: uuid.UUID,
    content: bytes,
    mime_type: str,
    filename: str,
    settings: Settings,
) -> tuple[StorageRef, dict[str, Any]]:
    """
    Upload is outside the Postgres transaction. Callers must remove `ref` if
    they abort after a successful upload so objects are not left orphaned.
    """
    extension = validate_upload(content, mime_type, settings.max_upload_bytes)
    token = uuid.uuid4().hex[:12]
    ref = StorageRef(
        bucket=settings.bucket_product_images,
        key=chat_attachment_key(conversation_id, token, extension),
    )
    storage = get_storage()
    try:
        await storage.upload(ref, content, mime_type or "application/octet-stream")
    except Exception as error:
        try:
            await storage.remove(ref)
        except Exception:
            logger.warning("could not clean up failed chat upload %s", ref.to_path())
        raise guard_storage_failure(error) from error
    return ref, {
        "name": filename or f"attachment.{extension}",
        "mime_type": mime_type,
        "storage_path": ref.to_path(),
    }


async def _remove_quietly(ref: StorageRef | None) -> None:
    if ref is None:
        return
    try:
        await get_storage().remove(ref)
    except Exception:
        logger.warning("could not remove chat object %s", ref.to_path())


def _storage_refs_from_conversation(
    messages: list[ChatMessage], artifacts: list[ChatArtifact]
) -> list[StorageRef]:
    refs: list[StorageRef] = []
    for message in messages:
        attachment = (message.metadata_json or {}).get("attachment") or {}
        path = attachment.get("storage_path")
        if isinstance(path, str):
            parsed = parse(path)
            if parsed is not None:
                refs.append(parsed)
    for artifact in artifacts:
        if artifact.storage_path:
            parsed = parse(artifact.storage_path)
            if parsed is not None:
                refs.append(parsed)
    return refs


async def create_conversation_with_message(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    body: CreateMessageIn,
    settings: Settings,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "",
    attachment_name: str = "",
) -> ChatConversation:
    content = (body.content or "").strip()
    if not content and not attachment_bytes:
        raise invalid(messages.CHAT_MESSAGE_REQUIRED)
    if len(content) > MAX_MESSAGE_CHARS:
        raise invalid(messages.CHAT_MESSAGE_TOO_LONG)

    language = body.language
    conversation = ChatConversation(
        user_id=user_id,
        title=title_from_content(content, language),
        language=language,
        active_theme_json=snapshot_dict(body.active_theme),
    )
    session.add(conversation)
    await session.flush()

    message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=content,
        language=language,
        metadata_json=_message_metadata(body, None),
    )
    session.add(message)
    await session.flush()

    uploaded: StorageRef | None = None
    try:
        if attachment_bytes:
            uploaded, attachment_meta = await store_chat_attachment(
                conversation_id=conversation.id,
                content=attachment_bytes,
                mime_type=attachment_mime,
                filename=attachment_name,
                settings=settings,
            )
            message.metadata_json = _message_metadata(body, attachment_meta)
            flag_modified(message, "metadata_json")
        conversation.updated_at = datetime.now(UTC)
        await session.flush()
        return conversation
    except Exception:
        await _remove_quietly(uploaded)
        raise


async def add_user_message(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    body: CreateMessageIn,
    settings: Settings,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "",
    attachment_name: str = "",
) -> ChatConversation:
    content = (body.content or "").strip()
    if not content and not attachment_bytes:
        raise invalid(messages.CHAT_MESSAGE_REQUIRED)
    if len(content) > MAX_MESSAGE_CHARS:
        raise invalid(messages.CHAT_MESSAGE_TOO_LONG)

    language = body.language or conversation.language
    message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=content,
        language=language,
        metadata_json=_message_metadata(body, None),
    )
    session.add(message)
    await session.flush()

    uploaded: StorageRef | None = None
    try:
        if attachment_bytes:
            uploaded, attachment_meta = await store_chat_attachment(
                conversation_id=conversation.id,
                content=attachment_bytes,
                mime_type=attachment_mime,
                filename=attachment_name,
                settings=settings,
            )
            message.metadata_json = _message_metadata(body, attachment_meta)
            flag_modified(message, "metadata_json")
        if conversation.title in {"گفتگوی جدید", "New chat"} and content:
            conversation.title = title_from_content(content, language)
        if language:
            conversation.language = language
        conversation.updated_at = datetime.now(UTC)
        await session.flush()
        return conversation
    except Exception:
        await _remove_quietly(uploaded)
        raise


async def list_conversations(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    archived: bool = False,
    query: str | None = None,
    limit: int = CHAT_LIST_LIMIT_DEFAULT,
    offset: int = 0,
) -> list[ChatConversation]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    stmt = select(ChatConversation).where(
        ChatConversation.user_id == user_id,
        ChatConversation.archived.is_(archived),
    )
    needle = (query or "").strip()
    if needle:
        pattern = f"%{_escape_like(needle)}%"
        message_match = exists(
            select(ChatMessage.id).where(
                ChatMessage.conversation_id == ChatConversation.id,
                ChatMessage.content.ilike(pattern, escape="\\"),
            )
        )
        stmt = stmt.where(
            or_(
                ChatConversation.title.ilike(pattern, escape="\\"),
                message_match,
            )
        )
    stmt = (
        stmt.order_by(ChatConversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(stmt))


async def load_conversation_page(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    limit: int = CHAT_MESSAGE_LIMIT_DEFAULT,
    before: datetime | None = None,
) -> tuple[list[ChatMessage], list[ChatArtifact], bool]:
    limit = max(1, min(limit, 500))
    stmt = select(ChatMessage).where(
        ChatMessage.conversation_id == conversation.id
    )
    if before is not None:
        stmt = stmt.where(ChatMessage.created_at < before)
    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit + 1)
    rows = list(await session.scalars(stmt))
    has_older = len(rows) > limit
    messages = list(reversed(rows[:limit]))
    message_ids = [item.id for item in messages]
    artifact_stmt = select(ChatArtifact).where(
        ChatArtifact.conversation_id == conversation.id
    )
    if message_ids:
        artifact_stmt = artifact_stmt.where(
            or_(
                ChatArtifact.message_id.in_(message_ids),
                ChatArtifact.message_id.is_(None),
            )
        )
    artifacts = list(
        await session.scalars(artifact_stmt.order_by(ChatArtifact.created_at))
    )
    return messages, artifacts, has_older


async def conversation_is_generating(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    exclude_assistant_id: uuid.UUID | None = None,
) -> bool:
    artifact_stmt = select(ChatArtifact.id).where(
        ChatArtifact.conversation_id == conversation_id,
        ChatArtifact.status == "generating",
    )
    if await session.scalar(artifact_stmt.limit(1)):
        return True
    messages = list(
        await session.scalars(
            select(ChatMessage).where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.role == "assistant",
            )
        )
    )
    for item in messages:
        if exclude_assistant_id is not None and item.id == exclude_assistant_id:
            continue
        if (item.metadata_json or {}).get("status") == "generating":
            return True
    return False


async def patch_conversation(
    conversation: ChatConversation,
    body: ConversationPatchIn,
) -> ChatConversation:
    fields = body.model_fields_set
    if "title" in fields:
        title = (body.title or "").strip()
        if not title:
            raise invalid(messages.CHAT_TITLE_REQUIRED)
        conversation.title = title
    if "pinned" in fields and body.pinned is not None:
        conversation.pinned = body.pinned
        conversation.pinned_at = datetime.now(UTC) if body.pinned else None
        if body.pinned:
            conversation.archived = False
    if "archived" in fields and body.archived is not None:
        conversation.archived = body.archived
        if body.archived:
            conversation.pinned = False
            conversation.pinned_at = None
    if "active_theme" in fields:
        conversation.active_theme_json = snapshot_dict(body.active_theme)
    conversation.updated_at = datetime.now(UTC)
    return conversation


async def delete_conversation(
    session: AsyncSession, conversation: ChatConversation
) -> None:
    messages = list(
        await session.scalars(
            select(ChatMessage).where(
                ChatMessage.conversation_id == conversation.id
            )
        )
    )
    artifacts = list(
        await session.scalars(
            select(ChatArtifact).where(
                ChatArtifact.conversation_id == conversation.id
            )
        )
    )
    refs = _storage_refs_from_conversation(messages, artifacts)
    await session.delete(conversation)
    await session.flush()
    for ref in refs:
        if not ref.key.startswith("chat/"):
            continue
        await _remove_quietly(ref)
