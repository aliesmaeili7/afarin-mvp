"""Conversation-scoped image reference resolution. Ownership is re-checked here."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.services.orchestrator.edit_text import is_deictic_latest

ResolutionSource = Literal[
    "none",
    "explicit_ids",
    "attachment",
    "deictic_latest",
    "sole_image",
]


@dataclass(frozen=True, slots=True)
class ReferenceResolution:
    artifacts: tuple[ChatArtifact, ...]
    source: ResolutionSource
    ambiguous: bool
    clarification_needed: bool
    attachment_message_id: uuid.UUID | None = None
    attachment_path: str | None = None
    attachment_mime: str | None = None

    def artifact_ids(self) -> list[uuid.UUID]:
        return [item.id for item in self.artifacts]

    def has_image(self) -> bool:
        return bool(self.artifacts) or bool(self.attachment_path)

    def as_context(self) -> dict[str, Any]:
        if self.ambiguous:
            status = "ambiguous"
        elif self.has_image():
            status = "resolved"
        else:
            status = "none"
        return {
            "status": status,
            "source": self.source,
            "artifact_ids": [str(item.id) for item in self.artifacts],
            "has_attachment": bool(self.attachment_path),
            "explicitly_referenced_this_turn": self.source == "explicit_ids",
        }


async def resolve_reference_artifacts(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    user_message: ChatMessage,
    explicit_ids: list[uuid.UUID],
) -> ReferenceResolution:
    """
    Resolve at most one primary image in the current conversation.

    Foreign / missing / failed IDs look like an empty resolution. Do not leak
    whether another user's artifact exists.
    """
    conversation = await session.get(ChatConversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        return ReferenceResolution(
            artifacts=(),
            source="none",
            ambiguous=False,
            clarification_needed=True,
        )
    ready = await _ready_images(session, conversation_id)
    owned = {item.id: item for item in ready}

    valid_explicit = tuple(
        owned[item_id] for item_id in explicit_ids if item_id in owned
    )
    if explicit_ids:
        if len(valid_explicit) == 1:
            return ReferenceResolution(
                artifacts=(valid_explicit[0],),
                source="explicit_ids",
                ambiguous=False,
                clarification_needed=False,
            )
        if len(valid_explicit) > 1:
            return ReferenceResolution(
                artifacts=(),
                source="none",
                ambiguous=True,
                clarification_needed=True,
            )
        return ReferenceResolution(
            artifacts=(),
            source="none",
            ambiguous=False,
            clarification_needed=True,
        )

    attachment = _image_attachment(user_message)
    if attachment is not None:
        path, mime = attachment
        return ReferenceResolution(
            artifacts=(),
            source="attachment",
            ambiguous=False,
            clarification_needed=False,
            attachment_message_id=user_message.id,
            attachment_path=path,
            attachment_mime=mime,
        )

    text = user_message.content or ""
    if is_deictic_latest(text) and ready:
        return ReferenceResolution(
            artifacts=(ready[-1],),
            source="deictic_latest",
            ambiguous=False,
            clarification_needed=False,
        )
    if len(ready) == 1:
        return ReferenceResolution(
            artifacts=(ready[0],),
            source="sole_image",
            ambiguous=False,
            clarification_needed=False,
        )
    if len(ready) > 1:
        return ReferenceResolution(
            artifacts=(),
            source="none",
            ambiguous=True,
            clarification_needed=True,
        )
    return ReferenceResolution(
        artifacts=(),
        source="none",
        ambiguous=False,
        clarification_needed=True,
    )


async def _ready_images(
    session: AsyncSession, conversation_id: uuid.UUID
) -> list[ChatArtifact]:
    rows = list(
        await session.scalars(
            select(ChatArtifact)
            .where(
                ChatArtifact.conversation_id == conversation_id,
                ChatArtifact.artifact_type == "image",
                ChatArtifact.status == "ready",
            )
            .order_by(ChatArtifact.created_at.asc())
        )
    )
    return [item for item in rows if item.storage_path]


def _image_attachment(message: ChatMessage) -> tuple[str, str] | None:
    attachment = (message.metadata_json or {}).get("attachment") or {}
    path = attachment.get("storage_path")
    mime = str(attachment.get("mime_type") or "image/png")
    if isinstance(path, str) and path and mime.startswith("image/"):
        return path, mime
    if isinstance(path, str) and path:
        return path, mime
    return None
