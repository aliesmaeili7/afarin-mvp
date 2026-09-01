"""Bounded Orchestrator input. Never dump the whole conversation."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.services.orchestrator.reference import resolve_reference_artifacts

MAX_MESSAGES = 12
MAX_ARTIFACTS = 5


class BoundedChatContext(BaseModel):
    conversation_id: uuid.UUID
    latest_user_text: str
    latest_user_message_id: uuid.UUID
    explicit_skill_hint: str | None = None
    reference_artifact_ids: list[uuid.UUID] = []
    active_theme: dict[str, Any] | None = None
    recent_messages: list[dict[str, Any]]
    recent_artifacts: list[dict[str, Any]]
    has_product_image: bool = False
    recent_route: str | None = None
    reference_resolution: dict[str, Any] | None = None
    has_ready_image_reference: bool = False


async def build_bounded_context(
    session: AsyncSession,
    conversation: ChatConversation,
    user_message: ChatMessage,
) -> BoundedChatContext:
    meta = dict(user_message.metadata_json or {})
    hint = meta.get("explicit_skill_hint")
    hint_text = hint if isinstance(hint, str) else None
    raw_refs = meta.get("reference_artifact_ids") or []
    ref_ids = [
        uuid.UUID(str(item))
        for item in raw_refs
        if item is not None
    ]

    messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(MAX_MESSAGES)
        )
    )
    messages.reverse()
    artifacts = list(
        await session.scalars(
            select(ChatArtifact)
            .where(
                ChatArtifact.conversation_id == conversation.id,
                ChatArtifact.status == "ready",
            )
            .order_by(ChatArtifact.created_at.desc())
            .limit(MAX_ARTIFACTS)
        )
    )
    artifacts.reverse()

    recent_route = None
    for item in reversed(messages):
        if item.role != "assistant":
            continue
        route = (item.metadata_json or {}).get("route")
        if isinstance(route, str):
            recent_route = route
            break

    resolution = await resolve_reference_artifacts(
        session,
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        user_message=user_message,
        explicit_ids=ref_ids,
    )
    has_image = _has_product_image(
        messages, artifacts, ref_ids
    ) or _has_campaign_product(artifacts)

    return BoundedChatContext(
        conversation_id=conversation.id,
        latest_user_text=user_message.content or "",
        latest_user_message_id=user_message.id,
        explicit_skill_hint=hint_text,
        reference_artifact_ids=ref_ids,
        active_theme=conversation.active_theme_json,
        recent_messages=[
            {
                "role": item.role,
                "content": (item.content or "")[:500],
                "language": item.language,
                "has_attachment": bool(
                    (item.metadata_json or {}).get("attachment")
                ),
            }
            for item in messages
        ],
        recent_artifacts=[
            {
                "id": str(item.id),
                "artifact_type": item.artifact_type,
                "aspect_ratio": item.aspect_ratio,
                "skill": (item.metadata_json or {}).get("skill"),
                "origin_route": (item.metadata_json or {}).get("skill"),
                "source_domain": (item.metadata_json or {}).get("source_domain"),
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "explicitly_referenced_this_turn": item.id in set(ref_ids),
            }
            for item in artifacts
        ],
        has_product_image=has_image,
        recent_route=recent_route,
        reference_resolution=resolution.as_context(),
        has_ready_image_reference=resolution.has_image(),
    )


def _has_product_image(
    messages: list[ChatMessage],
    artifacts: list[ChatArtifact],
    reference_ids: list[uuid.UUID],
) -> bool:
    for item in messages:
        attachment = (item.metadata_json or {}).get("attachment") or {}
        path = attachment.get("storage_path")
        mime = str(attachment.get("mime_type") or "")
        if isinstance(path, str) and path and mime.startswith("image/"):
            return True
        if isinstance(path, str) and path:
            return True
    if not reference_ids:
        return False
    wanted = set(reference_ids)
    return any(item.id in wanted and item.storage_path for item in artifacts)


def _has_campaign_product(artifacts: list[ChatArtifact]) -> bool:
    for item in artifacts:
        meta = item.metadata_json or {}
        if meta.get("campaign_id") or (
            meta.get("skill") == "advertising" and meta.get("source_domain_id")
        ):
            return True
    return False


def context_as_user_payload(context: BoundedChatContext) -> str:
    import json

    payload = context.model_dump(mode="json")
    payload.pop("conversation_id", None)
    payload.pop("latest_user_message_id", None)
    return json.dumps(payload, ensure_ascii=False)
