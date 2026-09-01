"""
Chat endpoints. Persistence stays in services.chat; generation is Orchestrator.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.errors import conflict, invalid
from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.schemas.chat import (
    CHAT_LIST_LIMIT_DEFAULT,
    CHAT_MESSAGE_LIMIT_DEFAULT,
    ConversationOut,
    ConversationPatchIn,
    ConversationSummaryOut,
    CreateMessageIn,
    ThemeSnapshot,
)
from app.services.chat import get_owned_chat_conversation, require_chat_user
from app.services.chat import service as chat_service
from app.services.identity.service import get_or_create_profile
from app.services.orchestrator.service import (
    execute_skill_job,
    handle_chat_turn,
    retry_failed_turn,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def _theme_out(raw: dict | None) -> ThemeSnapshot | None:
    if not raw:
        return None
    try:
        return ThemeSnapshot.model_validate(raw)
    except Exception:
        logger.warning("dropping invalid chat theme snapshot")
        return None


def to_summary(row: ChatConversation) -> ConversationSummaryOut:
    return ConversationSummaryOut(
        id=row.id,
        title=row.title,
        language=row.language,
        active_theme=_theme_out(row.active_theme_json),
        pinned=row.pinned,
        archived=row.archived,
        pinned_at=row.pinned_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_detail(
    row: ChatConversation,
    messages: list[ChatMessage],
    artifacts: list[ChatArtifact],
    has_older: bool,
) -> ConversationOut:
    return ConversationOut(
        id=row.id,
        title=row.title,
        language=row.language,
        active_theme=_theme_out(row.active_theme_json),
        pinned=row.pinned,
        archived=row.archived,
        pinned_at=row.pinned_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        messages=messages,
        artifacts=artifacts,
        has_older_messages=has_older,
    )


async def _read_message_payload(
    request: Request,
) -> tuple[CreateMessageIn, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        raw = form.get("payload")
        if hasattr(raw, "read"):
            raw = (await raw.read()).decode()
        elif isinstance(raw, bytes):
            raw = raw.decode()
        if not isinstance(raw, str) or not raw.strip():
            raise invalid(messages.GENERIC)
        try:
            body = CreateMessageIn.model_validate_json(raw)
        except Exception as error:
            raise invalid(messages.GENERIC) from error
        upload: UploadFile | None = None
        for _key, value in form.multi_items():
            if hasattr(value, "filename") and getattr(value, "filename", None):
                upload = value  # type: ignore[assignment]
                break
        return body, upload
    try:
        payload = await request.json()
    except json.JSONDecodeError as error:
        raise invalid(messages.GENERIC) from error
    try:
        return CreateMessageIn.model_validate(payload), None
    except Exception as error:
        raise invalid(messages.GENERIC) from error


async def _attachment_bytes(
    upload: UploadFile | None,
) -> tuple[bytes | None, str, str]:
    if upload is None:
        return None, "", ""
    content = await upload.read()
    if not content:
        return None, "", ""
    return content, upload.content_type or "", upload.filename or "attachment"


async def _detail(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    limit: int,
    before: datetime | None,
) -> ConversationOut:
    messages, artifacts, has_older = await chat_service.load_conversation_page(
        session, conversation, limit=limit, before=before
    )
    return to_detail(conversation, messages, artifacts, has_older)


async def _finish_turn(
    session: AsyncSession,
    conversation: ChatConversation,
    background: BackgroundTasks,
    settings,
) -> ConversationOut:
    conversation_id = conversation.id
    task = await handle_chat_turn(session, conversation, settings=settings)
    if task is not None:
        background.add_task(execute_skill_job, task)
        session.expunge_all()
    conversation = await session.get(ChatConversation, conversation_id) or conversation
    return await _detail(
        session, conversation, limit=CHAT_MESSAGE_LIMIT_DEFAULT, before=None
    )


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    request: Request,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
    background: BackgroundTasks,
) -> ConversationOut:
    user_id = require_chat_user(principal)
    await get_or_create_profile(session, user_id, principal.email)
    body, upload = await _read_message_payload(request)
    content, mime, name = await _attachment_bytes(upload)
    conversation = await chat_service.create_conversation_with_message(
        session,
        user_id=user_id,
        body=body,
        settings=settings,
        attachment_bytes=content,
        attachment_mime=mime,
        attachment_name=name,
    )
    return await _finish_turn(session, conversation, background, settings)


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def list_conversations(
    session: SessionDep,
    principal: PrincipalDep,
    archived: bool = False,
    q: str | None = None,
    limit: int = CHAT_LIST_LIMIT_DEFAULT,
    offset: int = 0,
) -> list[ConversationSummaryOut]:
    if principal.user_id is None:
        return []
    rows = await chat_service.list_conversations(
        session,
        principal.user_id,
        archived=archived,
        query=q,
        limit=limit,
        offset=offset,
    )
    return [to_summary(row) for row in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    limit: int = CHAT_MESSAGE_LIMIT_DEFAULT,
    before: datetime | None = None,
) -> ConversationOut:
    conversation = await get_owned_chat_conversation(
        session, principal, conversation_id
    )
    return await _detail(session, conversation, limit=limit, before=before)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def patch_conversation(
    conversation_id: uuid.UUID,
    body: ConversationPatchIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> ConversationOut:
    conversation = await get_owned_chat_conversation(
        session, principal, conversation_id
    )
    await chat_service.patch_conversation(conversation, body)
    await session.flush()
    return await _detail(
        session, conversation, limit=CHAT_MESSAGE_LIMIT_DEFAULT, before=None
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> None:
    conversation = await get_owned_chat_conversation(
        session, principal, conversation_id
    )
    await chat_service.delete_conversation(session, conversation)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationOut,
)
async def create_message(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
    background: BackgroundTasks,
) -> ConversationOut:
    conversation = await get_owned_chat_conversation(
        session, principal, conversation_id
    )
    if await chat_service.conversation_is_generating(session, conversation.id):
        raise conflict(messages.CHAT_BUSY)
    body, upload = await _read_message_payload(request)
    content, mime, name = await _attachment_bytes(upload)
    conversation = await chat_service.add_user_message(
        session,
        conversation,
        body=body,
        settings=settings,
        attachment_bytes=content,
        attachment_mime=mime,
        attachment_name=name,
    )
    return await _finish_turn(session, conversation, background, settings)


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/retry",
    response_model=ConversationOut,
)
async def retry_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
    background: BackgroundTasks,
) -> ConversationOut:
    conversation = await get_owned_chat_conversation(
        session, principal, conversation_id
    )
    task = await retry_failed_turn(
        session, conversation, message_id, settings=settings
    )
    if task is not None:
        background.add_task(execute_skill_job, task)
        session.expunge_all()
    conversation = await session.get(ChatConversation, conversation_id) or conversation
    return await _detail(
        session, conversation, limit=CHAT_MESSAGE_LIMIT_DEFAULT, before=None
    )
