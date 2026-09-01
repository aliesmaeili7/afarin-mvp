"""
One chat turn: persist is already done. Route, then talk or generate.

Generation never reuses the request session. `execute_skill_job` always opens
a fresh session via get_sessionmaker(), matching education._run_background.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core import messages
from app.core.config import Settings, get_settings
from app.core.errors import conflict, not_found
from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.db.session import get_sessionmaker
from app.services.chat import service as chat_service
from app.services.orchestrator.activity import preparing_phase_for
from app.services.orchestrator.context import build_bounded_context
from app.services.orchestrator.edit_text import parse_target_aspect
from app.services.orchestrator.language import (
    ChatLanguage,
    artifact_language,
    reply_language,
    requested_image_count,
)
from app.services.orchestrator.provider import get_orchestrator_provider
from app.services.orchestrator.schema import OrchestratorDecision, Route
from app.services.orchestrator.skills.base import SkillContext, SkillResult
from app.services.orchestrator.skills.registry import skill_for
from app.services.orchestrator.texts import (
    ACK,
    CLARIFY_ADS,
    CLARIFY_EDIT,
    CLARIFY_EDIT_AMBIGUOUS,
    CLARIFY_IMAGE,
    EDIT_FAILED,
    TRY_AGAIN,
    ack_for,
    fallback_for,
)

logger = logging.getLogger(__name__)

PAID_ROUTES = frozenset({"advertising", "education", "general_image", "image_edit"})
_WEAK_IMAGE = re.compile(
    r"^(یه\s+)?(تصویر|عکس|image)(\s+بساز)?\.?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TurnTask:
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    artifact_ids: tuple[uuid.UUID, ...]
    route: Route
    reply_language: ChatLanguage
    artifact_language: ChatLanguage | None
    user_text: str
    generation_instruction: str | None
    requested_image_count: int
    reference_artifact_ids: tuple[uuid.UUID, ...]
    edit_instruction: str | None = None
    target_aspect_ratio: str | None = None
    source_artifact_ids: tuple[uuid.UUID, ...] = ()
    source_attachment_path: str | None = None
    source_message_id: uuid.UUID | None = None


async def handle_chat_turn(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    settings: Settings | None = None,
) -> TurnTask | None:
    """
    User message is already flushed. Commit it, then route.

    Returns a TurnTask when live image generation should run in BackgroundTasks.
    Stub providers run inline on a fresh session and return None.
    """
    active = settings or get_settings()
    user_message = await _latest_user_message(session, conversation.id)
    if user_message is None:
        return None

    if await chat_service.conversation_is_generating(session, conversation.id):
        raise conflict(messages.CHAT_BUSY)

    await session.commit()

    text = user_message.content or ""
    lang = reply_language(text)
    art_lang = artifact_language(text)
    hint = (user_message.metadata_json or {}).get("explicit_skill_hint")
    refs = _uuid_list((user_message.metadata_json or {}).get("reference_artifact_ids"))
    bounded = await build_bounded_context(session, conversation, user_message)

    if hint in PAID_ROUTES:
        decision = OrchestratorDecision(
            route=hint,
            reply_language=lang,
            artifact_language=art_lang,
            assistant_preamble=ACK[hint][lang],
            orchestrator_called=False,
        )
    else:
        try:
            decision = await get_orchestrator_provider().complete(bounded)
        except Exception:
            logger.exception("orchestrator failed")
            await _persist_text_assistant(
                session, conversation, TRY_AGAIN[lang], lang, route="clarify"
            )
            await session.commit()
            return None
        decision.reply_language = lang
        if art_lang is not None:
            decision.artifact_language = art_lang

    if decision.route == "advertising" and not bounded.has_product_image:
        await _persist_text_assistant(
            session,
            conversation,
            CLARIFY_ADS[lang],
            lang,
            route="clarify",
        )
        await session.commit()
        return None
    if decision.route == "general_image" and not _has_image_subject(
        text, bounded.has_product_image or bool(refs)
    ):
        await _persist_text_assistant(
            session,
            conversation,
            CLARIFY_IMAGE[lang],
            lang,
            route="clarify",
        )
        await session.commit()
        return None
    if decision.route == "image_edit":
        status = (bounded.reference_resolution or {}).get("status")
        if status == "ambiguous":
            await _persist_text_assistant(
                session,
                conversation,
                CLARIFY_EDIT_AMBIGUOUS[lang],
                lang,
                route="clarify",
                extra={"needs_clarification": True},
            )
            await session.commit()
            return None
        if not bounded.has_ready_image_reference:
            await _persist_text_assistant(
                session,
                conversation,
                CLARIFY_EDIT[lang],
                lang,
                route="clarify",
                extra={"needs_clarification": True},
            )
            await session.commit()
            return None

    if decision.route not in PAID_ROUTES:
        content = (decision.assistant_message or "").strip() or fallback_for(
            decision.route, lang
        )
        await _persist_text_assistant(
            session,
            conversation,
            content,
            lang,
            route=decision.route,
            extra={"needs_clarification": decision.needs_clarification},
        )
        await session.commit()
        return None

    count = decision.requested_image_count or requested_image_count(text)
    if count not in (1, 3):
        count = 1
    if decision.route != "advertising":
        count = 1

    edit_instruction = (decision.edit_instruction or text).strip() or text
    target_aspect = parse_target_aspect(text) or decision.target_aspect_ratio
    source_ids = _uuid_list(
        (bounded.reference_resolution or {}).get("artifact_ids")
    )
    attachment = (user_message.metadata_json or {}).get("attachment") or {}
    source_path = (
        attachment.get("storage_path")
        if isinstance(attachment.get("storage_path"), str)
        and not source_ids
        else None
    )
    source_message_id = user_message.id if source_path else None
    aspect = await _aspect_for_turn(
        session, decision.route, target_aspect, source_ids
    )

    preamble = (decision.assistant_preamble or "").strip() or ack_for(
        decision.route, lang
    )
    assistant, artifacts = await _persist_generating(
        session,
        conversation,
        content=preamble,
        language=lang,
        route=decision.route,
        count=count,
        aspect=aspect,
        extra={
            "artifact_language": decision.artifact_language,
            "generation_instruction": decision.generation_instruction,
            "edit_instruction": (
                edit_instruction if decision.route == "image_edit" else None
            ),
            "target_aspect_ratio": target_aspect,
            "source_artifact_ids": [str(item) for item in source_ids],
            "source_attachment_path": source_path,
            "source_message_id": str(source_message_id) if source_message_id else None,
            "requested_image_count": count,
            "orchestrator_called": decision.orchestrator_called,
        },
    )
    await session.commit()

    task = TurnTask(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        user_message_id=user_message.id,
        assistant_message_id=assistant.id,
        artifact_ids=tuple(item.id for item in artifacts),
        route=decision.route,
        reply_language=lang,
        artifact_language=decision.artifact_language,
        user_text=text,
        generation_instruction=decision.generation_instruction,
        requested_image_count=count,
        reference_artifact_ids=tuple(refs),
        edit_instruction=edit_instruction if decision.route == "image_edit" else None,
        target_aspect_ratio=target_aspect,
        source_artifact_ids=tuple(source_ids),
        source_attachment_path=source_path,
        source_message_id=source_message_id,
    )
    if _run_inline(active):
        await execute_skill_job(task)
        session.expunge_all()
        return None
    return task


async def retry_failed_turn(
    session: AsyncSession,
    conversation: ChatConversation,
    assistant_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> TurnTask | None:
    active = settings or get_settings()
    assistant = await session.get(ChatMessage, assistant_id)
    if (
        assistant is None
        or assistant.conversation_id != conversation.id
        or assistant.role != "assistant"
    ):
        raise not_found(messages.CHAT_NOT_FOUND)
    meta = dict(assistant.metadata_json or {})
    if not meta.get("retryable") and meta.get("status") != "failed":
        raise conflict(messages.CHAT_RETRY_NOT_ALLOWED)
    route = meta.get("route")
    if route not in PAID_ROUTES:
        raise conflict(messages.CHAT_RETRY_NOT_ALLOWED)
    if await chat_service.conversation_is_generating(
        session, conversation.id, exclude_assistant_id=assistant.id
    ):
        raise conflict(messages.CHAT_BUSY)

    artifacts = list(
        await session.scalars(
            select(ChatArtifact).where(
                ChatArtifact.conversation_id == conversation.id,
                ChatArtifact.message_id == assistant.id,
            )
        )
    )
    user_message = await _user_message_before(session, conversation.id, assistant)
    text = user_message.content if user_message else ""
    lang: ChatLanguage = (
        assistant.language if assistant.language in ("fa", "en") else "fa"
    )
    art_lang = meta.get("artifact_language")
    if art_lang not in ("fa", "en"):
        art_lang = artifact_language(text)
    count = int(meta.get("requested_image_count") or 1)
    if count not in (1, 3):
        count = 1
    refs = _uuid_list(
        (user_message.metadata_json or {}).get("reference_artifact_ids")
        if user_message
        else []
    )
    source_ids = _uuid_list(meta.get("source_artifact_ids"))
    if not source_ids:
        source_ids = list(refs)
    source_path = meta.get("source_attachment_path")
    if not isinstance(source_path, str):
        source_path = None
    source_message_raw = meta.get("source_message_id")
    try:
        source_message_id = (
            uuid.UUID(str(source_message_raw)) if source_message_raw else None
        )
    except (ValueError, TypeError):
        source_message_id = None
    edit_instruction = meta.get("edit_instruction")
    if not isinstance(edit_instruction, str):
        edit_instruction = None
    target_aspect = meta.get("target_aspect_ratio")
    if target_aspect not in ("1:1", "4:5", "9:16"):
        target_aspect = None

    meta["status"] = "generating"
    meta["failed"] = False
    meta["retryable"] = False
    meta["activity_phase"] = preparing_phase_for(route)
    assistant.metadata_json = meta
    flag_modified(assistant, "metadata_json")
    assistant.content = ack_for(route, lang)
    for artifact in artifacts:
        artifact.status = "generating"
        artifact.storage_path = None
        extra = dict(artifact.metadata_json or {})
        extra.pop("error", None)
        artifact.metadata_json = extra
        flag_modified(artifact, "metadata_json")
    conversation.updated_at = datetime.now(UTC)
    await session.commit()

    task = TurnTask(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        user_message_id=user_message.id if user_message else assistant.id,
        assistant_message_id=assistant.id,
        artifact_ids=tuple(item.id for item in artifacts),
        route=route,
        reply_language=lang,
        artifact_language=art_lang,
        user_text=text,
        generation_instruction=meta.get("generation_instruction"),
        requested_image_count=count,
        reference_artifact_ids=tuple(refs),
        edit_instruction=edit_instruction,
        target_aspect_ratio=target_aspect,
        source_artifact_ids=tuple(source_ids),
        source_attachment_path=source_path,
        source_message_id=source_message_id,
    )
    if _run_inline(active):
        await execute_skill_job(task)
        session.expunge_all()
        return None
    return task


async def execute_skill_job(task: TurnTask) -> None:
    async with get_sessionmaker()() as session:
        try:
            conversation = await session.get(ChatConversation, task.conversation_id)
            if conversation is None or conversation.user_id != task.user_id:
                return
            assistant = await session.get(ChatMessage, task.assistant_message_id)
            user_message = await session.get(ChatMessage, task.user_message_id)
            if assistant is None:
                return
            artifacts = []
            for artifact_id in task.artifact_ids:
                row = await session.get(ChatArtifact, artifact_id)
                if row is not None:
                    artifacts.append(row)
            if not artifacts:
                artifacts = list(
                    await session.scalars(
                        select(ChatArtifact).where(
                            ChatArtifact.message_id == assistant.id
                        )
                    )
                )
            skill = skill_for(task.route)
            if skill is None:
                raise RuntimeError(f"no skill for {task.route}")
            result = await skill.execute(
                session,
                SkillContext(
                    conversation=conversation,
                    user_message=user_message or assistant,
                    assistant_message=assistant,
                    artifacts=artifacts,
                    user_id=task.user_id,
                    user_text=task.user_text,
                    reply_language=task.reply_language,
                    artifact_language=task.artifact_language,
                    generation_instruction=task.generation_instruction,
                    requested_image_count=task.requested_image_count,
                    active_theme=conversation.active_theme_json,
                    reference_artifact_ids=list(task.reference_artifact_ids),
                    route=task.route,
                    edit_instruction=task.edit_instruction,
                    target_aspect_ratio=task.target_aspect_ratio,
                    source_artifact_ids=list(task.source_artifact_ids),
                    source_attachment_path=task.source_attachment_path,
                    source_message_id=task.source_message_id,
                ),
            )
            await _apply_success(session, conversation, assistant, artifacts, result)
            await session.commit()
        except Exception:
            logger.exception("chat skill %s failed", task.route)
            await session.rollback()
            async with get_sessionmaker()() as failed:
                await _mark_failed(failed, task)
                await failed.commit()


def _run_inline(settings: Settings) -> bool:
    return settings.image_provider == "stub"


async def _aspect_for_turn(
    session: AsyncSession,
    route: Route,
    target_aspect: str | None,
    source_ids: list[uuid.UUID],
) -> str:
    if target_aspect in ("1:1", "4:5", "9:16"):
        return target_aspect
    if route == "advertising":
        return "4:5"
    if source_ids:
        source = await session.get(ChatArtifact, source_ids[0])
        if source is not None and source.aspect_ratio in ("1:1", "4:5", "9:16"):
            return source.aspect_ratio
    return "1:1"


def _has_image_subject(text: str, has_reference: bool) -> bool:
    if has_reference:
        return True
    stripped = (text or "").strip()
    if len(stripped) < 3:
        return False
    return not bool(_WEAK_IMAGE.fullmatch(stripped))


def _uuid_list(raw: Any) -> list[uuid.UUID]:
    if not isinstance(raw, list):
        return []
    out: list[uuid.UUID] = []
    for item in raw:
        try:
            out.append(uuid.UUID(str(item)))
        except (ValueError, TypeError):
            continue
    return out


async def _latest_user_message(
    session: AsyncSession, conversation_id: uuid.UUID
) -> ChatMessage | None:
    return await session.scalar(
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role == "user",
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )


async def _user_message_before(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    assistant: ChatMessage,
) -> ChatMessage | None:
    return await session.scalar(
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role == "user",
            ChatMessage.created_at <= assistant.created_at,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )


async def _persist_text_assistant(
    session: AsyncSession,
    conversation: ChatConversation,
    content: str,
    language: ChatLanguage,
    *,
    route: str,
    extra: dict[str, Any] | None = None,
) -> ChatMessage:
    meta = {"route": route, "status": "ready"}
    if extra:
        meta.update(extra)
    row = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        language=language,
        metadata_json=meta,
    )
    session.add(row)
    conversation.updated_at = datetime.now(UTC)
    await session.flush()
    return row


async def _persist_generating(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    content: str,
    language: ChatLanguage,
    route: Route,
    count: int,
    extra: dict[str, Any],
    aspect: str | None = None,
) -> tuple[ChatMessage, list[ChatArtifact]]:
    assistant = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        language=language,
        metadata_json={
            "route": route,
            "status": "generating",
            "activity_phase": preparing_phase_for(route),
            **{key: value for key, value in extra.items() if value is not None},
        },
    )
    session.add(assistant)
    await session.flush()
    if aspect not in ("1:1", "4:5", "9:16"):
        aspect = "4:5" if route == "advertising" else "1:1"
    artifacts: list[ChatArtifact] = []
    for _ in range(max(1, count)):
        artifact = ChatArtifact(
            conversation_id=conversation.id,
            message_id=assistant.id,
            artifact_type="image",
            status="generating",
            aspect_ratio=aspect,
            metadata_json={"skill": route},
        )
        session.add(artifact)
        artifacts.append(artifact)
    conversation.updated_at = datetime.now(UTC)
    await session.flush()
    return assistant, artifacts


async def _apply_success(
    session: AsyncSession,
    conversation: ChatConversation,
    assistant: ChatMessage,
    artifacts: list[ChatArtifact],
    result: SkillResult,
) -> None:
    meta = dict(assistant.metadata_json or {})
    meta["status"] = "ready"
    meta["failed"] = False
    meta["retryable"] = False
    meta.pop("activity_phase", None)
    meta.update(result.metadata)
    assistant.metadata_json = meta
    flag_modified(assistant, "metadata_json")
    if result.assistant_content:
        assistant.content = result.assistant_content

    images = result.images
    for index, artifact in enumerate(artifacts):
        if index < len(images):
            produced = images[index]
            artifact.status = "ready"
            artifact.storage_path = produced.storage_path
            artifact.mime_type = produced.mime_type
            artifact.width = produced.width
            artifact.height = produced.height
            artifact.aspect_ratio = produced.aspect_ratio
            extra = dict(artifact.metadata_json or {})
            extra.update(produced.metadata)
            if produced.caption:
                extra["caption"] = produced.caption
            artifact.metadata_json = extra
            flag_modified(artifact, "metadata_json")
        else:
            artifact.status = "failed"
            extra = dict(artifact.metadata_json or {})
            extra["unused"] = True
            artifact.metadata_json = extra
            flag_modified(artifact, "metadata_json")

    for produced in images[len(artifacts) :]:
        session.add(
            ChatArtifact(
                conversation_id=conversation.id,
                message_id=assistant.id,
                artifact_type="image",
                storage_path=produced.storage_path,
                mime_type=produced.mime_type,
                width=produced.width,
                height=produced.height,
                aspect_ratio=produced.aspect_ratio,
                status="ready",
                metadata_json=produced.metadata,
            )
        )
    conversation.updated_at = datetime.now(UTC)
    await session.flush()


async def _mark_failed(session: AsyncSession, task: TurnTask) -> None:
    assistant = await session.get(ChatMessage, task.assistant_message_id)
    conversation = await session.get(ChatConversation, task.conversation_id)
    if assistant is None:
        return
    meta = dict(assistant.metadata_json or {})
    meta["status"] = "failed"
    meta["failed"] = True
    meta["retryable"] = True
    meta.pop("activity_phase", None)
    assistant.metadata_json = meta
    flag_modified(assistant, "metadata_json")
    lang: ChatLanguage = (
        assistant.language if assistant.language in ("fa", "en") else "fa"
    )
    if meta.get("route") == "image_edit":
        assistant.content = EDIT_FAILED[lang]
    else:
        assistant.content = ""
    artifacts = list(
        await session.scalars(
            select(ChatArtifact).where(ChatArtifact.message_id == assistant.id)
        )
    )
    for artifact in artifacts:
        artifact.status = "failed"
        extra = dict(artifact.metadata_json or {})
        extra["retryable"] = True
        artifact.metadata_json = extra
        flag_modified(artifact, "metadata_json")
    if conversation is not None:
        conversation.updated_at = datetime.now(UTC)
    await session.flush()
