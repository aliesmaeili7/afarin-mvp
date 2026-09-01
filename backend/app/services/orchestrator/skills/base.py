"""Chat skill protocol. Skills talk to in-process Python services, never HTTP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatArtifact, ChatConversation, ChatMessage
from app.services.orchestrator.language import ChatLanguage
from app.services.orchestrator.schema import Route


@dataclass
class SkillContext:
    conversation: ChatConversation
    user_message: ChatMessage
    assistant_message: ChatMessage
    artifacts: list[ChatArtifact]
    user_id: uuid.UUID
    user_text: str
    reply_language: ChatLanguage
    artifact_language: ChatLanguage | None
    generation_instruction: str | None
    requested_image_count: int
    active_theme: dict[str, Any] | None
    reference_artifact_ids: list[uuid.UUID]
    route: Route
    edit_instruction: str | None = None
    target_aspect_ratio: str | None = None
    source_artifact_ids: list[uuid.UUID] = field(default_factory=list)
    source_attachment_path: str | None = None
    source_message_id: uuid.UUID | None = None


@dataclass
class ProducedImage:
    storage_path: str
    mime_type: str = "image/jpeg"
    width: int | None = None
    height: int | None = None
    aspect_ratio: str = "1:1"
    metadata: dict[str, Any] = field(default_factory=dict)
    caption: str | None = None


@dataclass
class SkillResult:
    images: list[ProducedImage]
    assistant_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChatSkill(Protocol):
    name: str

    async def execute(
        self, session: AsyncSession, context: SkillContext
    ) -> SkillResult: ...
