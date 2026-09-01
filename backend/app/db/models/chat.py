"""
Generic chat persistence. Phase B only: conversations, messages, artifacts.

Not a Campaign and not an EducationalPost. Skills will later hang off message
metadata; the conversation itself has no skill identity.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    CHAT_ARTIFACT_ASPECTS,
    CHAT_ARTIFACT_STATUSES,
    CHAT_ARTIFACT_TYPES,
    CHAT_LANGUAGES,
    CHAT_ROLES,
)
from app.db.base import (
    Base,
    created_timestamp,
    enum_check,
    json_column,
    pk,
    text_column,
    updated_timestamp,
    user_fk,
)


class ChatConversation(Base):
    """
    A user-owned chat thread. Created on the first authenticated send, never
    merely because `/chat` was opened.
    """

    __tablename__ = "chat_conversations"
    __table_args__ = (
        enum_check("chat_conversations", "language", CHAT_LANGUAGES, nullable=True),
        Index(
            "ix_chat_conversations_user_updated",
            "user_id",
            text("updated_at desc"),
        ),
        Index(
            "ix_chat_conversations_user_archived",
            "user_id",
            "archived",
            text("updated_at desc"),
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str | None] = text_column()
    #: Semantic snapshot: id, source, name, style_json. Not CSS/swatches.
    active_theme_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    pinned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    artifacts: Mapped[list[ChatArtifact]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatArtifact.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        enum_check("chat_messages", "role", CHAT_ROLES),
        enum_check("chat_messages", "language", CHAT_LANGUAGES, nullable=True),
        Index(
            "ix_chat_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("''")
    )
    language: Mapped[str | None] = text_column()
    metadata_json: Mapped[dict] = json_column("metadata_json")
    created_at: Mapped[datetime] = created_timestamp()

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")
    artifacts: Mapped[list[ChatArtifact]] = relationship(back_populates="message")


class ChatArtifact(Base):
    __tablename__ = "chat_artifacts"
    __table_args__ = (
        enum_check("chat_artifacts", "artifact_type", CHAT_ARTIFACT_TYPES),
        enum_check(
            "chat_artifacts", "status", CHAT_ARTIFACT_STATUSES, nullable=True
        ),
        enum_check(
            "chat_artifacts", "aspect_ratio", CHAT_ARTIFACT_ASPECTS, nullable=True
        ),
        Index("ix_chat_artifacts_conversation", "conversation_id"),
        Index("ix_chat_artifacts_message", "message_id"),
    )

    id: Mapped[uuid.UUID] = pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'image'")
    )
    storage_path: Mapped[str | None] = text_column()
    mime_type: Mapped[str | None] = text_column()
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[str | None] = text_column()
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'ready'")
    )
    metadata_json: Mapped[dict] = json_column("metadata_json")
    created_at: Mapped[datetime] = created_timestamp()

    conversation: Mapped[ChatConversation] = relationship(back_populates="artifacts")
    message: Mapped[ChatMessage | None] = relationship(back_populates="artifacts")
