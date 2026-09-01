"""chat persistence phase b

Revision ID: c5f8a2d01b34
Revises: b4e7f1c92a05
Create Date: 2026-09-01 20:50:00.000000

Adds the generic chat domain: conversations, messages, and artifacts.
Authenticated-only ownership via profiles.user_id. No anonymous DB rows.
No advertising/education FKs — skills later hang off message metadata.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.models import BROWSER_ROLES, RUNTIME_ROLE

revision: str = "c5f8a2d01b34"
down_revision: str | None = "b4e7f1c92a05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY = "afarin_app_full_access"
NEW_TABLES = ("chat_conversations", "chat_messages", "chat_artifacts")


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("active_theme_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "pinned",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "language is null or language in ('fa', 'en')",
            name="ck_chat_conversations_language",
        ),
    )
    op.create_index(
        "ix_chat_conversations_user_id", "chat_conversations", ["user_id"]
    )
    op.create_index(
        "ix_chat_conversations_user_updated",
        "chat_conversations",
        ["user_id", sa.text("updated_at desc")],
    )
    op.create_index(
        "ix_chat_conversations_user_archived",
        "chat_conversations",
        ["user_id", "archived", sa.text("updated_at desc")],
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column(
            "content",
            sa.String(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "role in ('user', 'assistant')",
            name="ck_chat_messages_role",
        ),
        sa.CheckConstraint(
            "language is null or language in ('fa', 'en')",
            name="ck_chat_messages_language",
        ),
    )
    op.create_index(
        "ix_chat_messages_conversation_created",
        "chat_messages",
        ["conversation_id", "created_at"],
    )

    op.create_table(
        "chat_artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "artifact_type",
            sa.String(),
            server_default=sa.text("'image'"),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("aspect_ratio", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            server_default=sa.text("'ready'"),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "artifact_type in ('image', 'audio', 'video', 'subtitle', 'document')",
            name="ck_chat_artifacts_artifact_type",
        ),
        sa.CheckConstraint(
            "status is null or status in ('generating', 'ready', 'failed')",
            name="ck_chat_artifacts_status",
        ),
        sa.CheckConstraint(
            "aspect_ratio is null or aspect_ratio in ('1:1', '4:5')",
            name="ck_chat_artifacts_aspect_ratio",
        ),
    )
    op.create_index(
        "ix_chat_artifacts_conversation",
        "chat_artifacts",
        ["conversation_id"],
    )
    op.create_index(
        "ix_chat_artifacts_message",
        "chat_artifacts",
        ["message_id"],
    )

    browser_roles = ", ".join(BROWSER_ROLES)
    for table in NEW_TABLES:
        op.execute(f"alter table {table} enable row level security")
        op.execute(
            f"create policy {POLICY} on {table} "
            f"for all to {RUNTIME_ROLE} using (true) with check (true)"
        )
        op.execute(
            f"grant select, insert, update, delete on table {table} "
            f"to {RUNTIME_ROLE}"
        )
        op.execute(f"revoke all on table {table} from {browser_roles}")


def downgrade() -> None:
    op.drop_table("chat_artifacts")
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
