"""educational content phase 1

Revision ID: b4e7f1c92a05
Revises: a3c8d2e1f0b4
Create Date: 2026-08-27 17:40:00.000000

Adds the educational domain: reusable themes, one-prompt posts, and the two
job types that record educational agent and image spend. `generation_jobs`
gains a second parent so advertising and educational telemetry stay in one
table; `campaign_id` becomes nullable and an XOR check keeps every row owned
by exactly one of the two.

Educational content is authenticated-only, so `educational_posts.user_id` is
NOT NULL and there is no anonymous-session column to adopt later.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.models import BROWSER_ROLES, RUNTIME_ROLE

revision: str = "b4e7f1c92a05"
down_revision: str | None = "a3c8d2e1f0b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY = "afarin_app_full_access"
NEW_TABLES = ("educational_themes", "educational_posts")

JOB_TYPES_BEFORE = (
    "job_type in ('campaign_generation', 'concept_generation', "
    "'copy_rewrite', 'image_generation', 'visual_planner', "
    "'prompt_architect', 'creative_agent', 'visual_quality_check')"
)
JOB_TYPES_AFTER = (
    "job_type in ('campaign_generation', 'concept_generation', "
    "'copy_rewrite', 'image_generation', 'visual_planner', "
    "'prompt_architect', 'creative_agent', 'visual_quality_check', "
    "'educational_agent', 'educational_image')"
)


def upgrade() -> None:
    op.create_table(
        "educational_themes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "theme_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(),
            server_default=sa.text("'user'"),
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
            "source in ('builtin', 'user')",
            name="ck_educational_themes_source",
        ),
    )
    op.create_index(
        "ix_educational_themes_user_id", "educational_themes", ["user_id"]
    )
    op.create_index(
        "ix_educational_themes_user_created",
        "educational_themes",
        ["user_id", sa.text("created_at desc")],
    )

    op.create_table(
        "educational_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_prompt", sa.String(), nullable=False),
        sa.Column(
            "selected_theme_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("selected_builtin_theme_id", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column(
            "agent_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "theme_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "render_spec_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("image_storage_path", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("wall_time_ms", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["selected_theme_id"],
            ["educational_themes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status in ('queued', 'generating', 'ready', 'failed')",
            name="ck_educational_posts_status",
        ),
    )
    op.create_index(
        "ix_educational_posts_user_id", "educational_posts", ["user_id"]
    )
    op.create_index(
        "ix_educational_posts_selected_theme_id",
        "educational_posts",
        ["selected_theme_id"],
    )
    op.create_index(
        "ix_educational_posts_user_created",
        "educational_posts",
        ["user_id", sa.text("created_at desc")],
    )

    op.add_column(
        "generation_jobs",
        sa.Column(
            "educational_post_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_index(
        "ix_generation_jobs_educational_post_id",
        "generation_jobs",
        ["educational_post_id"],
    )
    op.create_foreign_key(
        "fk_generation_jobs_educational_post",
        "generation_jobs",
        "educational_posts",
        ["educational_post_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("generation_jobs", "campaign_id", nullable=True)
    op.create_check_constraint(
        "ck_generation_jobs_one_parent",
        "generation_jobs",
        "(campaign_id is not null) <> (educational_post_id is not null)",
    )
    op.create_index(
        "uq_generation_jobs_active_education",
        "generation_jobs",
        ["educational_post_id", "job_type"],
        unique=True,
        postgresql_where=sa.text(
            "status in ('queued', 'processing') "
            "AND job_type in ('educational_agent', 'educational_image')"
        ),
    )

    op.drop_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", type_="check"
    )
    op.create_check_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", JOB_TYPES_AFTER
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
    op.drop_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", type_="check"
    )
    op.create_check_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", JOB_TYPES_BEFORE
    )

    op.drop_index("uq_generation_jobs_active_education", table_name="generation_jobs")
    op.drop_constraint(
        "ck_generation_jobs_one_parent", "generation_jobs", type_="check"
    )
    # Educational rows have no campaign, so they must go before campaign_id
    # can be NOT NULL again.
    op.execute("delete from generation_jobs where campaign_id is null")
    op.alter_column("generation_jobs", "campaign_id", nullable=False)
    op.drop_constraint(
        "fk_generation_jobs_educational_post",
        "generation_jobs",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_generation_jobs_educational_post_id", table_name="generation_jobs"
    )
    op.drop_column("generation_jobs", "educational_post_id")

    op.drop_table("educational_posts")
    op.drop_table("educational_themes")
