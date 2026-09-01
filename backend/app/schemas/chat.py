"""Chat request and response bodies. Phase B: persistence only, no generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.domain import Id, Model, OptionalId, Timestamp

CHAT_LIST_LIMIT_DEFAULT = 50
CHAT_MESSAGE_LIMIT_DEFAULT = 200
MAX_MESSAGE_CHARS = 8000
TITLE_DISPLAY_CHARS = 28

SkillHint = Literal["advertising", "education", "general_image"]
ChatLanguage = Literal["fa", "en"]


class ThemeSnapshot(BaseModel):
    """Semantic conversation theme. Frontend-only CSS/swatches are ignored."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    style_json: dict[str, Any] = Field(default_factory=dict)


class CreateMessageIn(BaseModel):
    content: str = ""
    language: ChatLanguage | None = None
    action_hint: SkillHint | None = None
    active_theme: ThemeSnapshot | None = None


class ConversationPatchIn(BaseModel):
    title: str | None = None
    pinned: bool | None = None
    archived: bool | None = None
    active_theme: ThemeSnapshot | None = None


class ArtifactOut(Model):
    id: Id
    conversation_id: Id
    message_id: OptionalId = None
    artifact_type: str
    storage_path: str | None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str | None = None
    status: str
    metadata_json: dict[str, Any]
    created_at: Timestamp


class MessageOut(Model):
    id: Id
    conversation_id: Id
    role: str
    content: str
    language: str | None
    metadata_json: dict[str, Any]
    created_at: Timestamp


class ConversationSummaryOut(Model):
    id: Id
    title: str
    language: str | None
    active_theme: ThemeSnapshot | None
    pinned: bool
    archived: bool
    pinned_at: Timestamp | None
    created_at: Timestamp
    updated_at: Timestamp


class ConversationOut(ConversationSummaryOut):
    messages: list[MessageOut]
    artifacts: list[ArtifactOut]
    has_older_messages: bool = False
