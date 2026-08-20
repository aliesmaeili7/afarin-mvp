"""phase 4b creative visual attempts

Revision ID: d8c2f4a1b0e3
Revises: b7e4c1a90d12
Create Date: 2026-08-20 19:20:00.000000

Adds creative-mode recipe state, candidate history, and job types for the
visual planner and quality check. Accurate composite generation is unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.models import BROWSER_ROLES, RUNTIME_ROLE

revision: str = "d8c2f4a1b0e3"
down_revision: str | None = "b7e4c1a90d12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY = "afarin_app_full_access"
NEW_TABLES = ("campaign_visual_attempts", "campaign_visual_candidates")


def upgrade() -> None:
    op.drop_constraint("ck_campaigns_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaigns_status",
        "campaigns",
        "status in ('draft', 'brief_complete', 'concepts_ready', "
        "'concept_selected', 'queued', 'generating', 'candidates_ready', "
        "'ready', 'partial_failed', 'failed')",
    )

    op.add_column(
        "campaigns",
        sa.Column("visual_creation_mode", sa.String(), nullable=True),
    )
    op.create_check_constraint(
        "ck_campaigns_visual_creation_mode",
        "campaigns",
        "visual_creation_mode is null or visual_creation_mode in "
        "('accurate', 'creative')",
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "visual_recipe_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "current_visual_attempt_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_campaigns_current_visual_attempt_id",
        "campaigns",
        ["current_visual_attempt_id"],
    )

    op.create_table(
        "campaign_visual_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "recipe_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "planner_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "auto_repair_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "selected_candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "attempt_number",
            name="uq_visual_attempts_campaign_number",
        ),
        sa.CheckConstraint(
            "source in ('smart', 'custom')",
            name="ck_campaign_visual_attempts_source",
        ),
        sa.CheckConstraint(
            "status in ('generating', 'awaiting_selection', 'selected', "
            "'superseded')",
            name="ck_campaign_visual_attempts_status",
        ),
    )
    op.create_index(
        "ix_campaign_visual_attempts_campaign_id",
        "campaign_visual_attempts",
        ["campaign_id"],
    )

    op.create_table(
        "campaign_visual_candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.String(),
            server_default=sa.text("'primary'"),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column(
            "quality_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "hard_failed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "hidden",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "generation_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "variation_index",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["campaign_visual_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generation_job_id"],
            ["generation_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "kind in ('primary', 'repair')",
            name="ck_campaign_visual_candidates_kind",
        ),
    )
    op.create_index(
        "ix_campaign_visual_candidates_attempt_id",
        "campaign_visual_candidates",
        ["attempt_id"],
    )

    op.create_foreign_key(
        "fk_visual_attempts_selected_candidate",
        "campaign_visual_attempts",
        "campaign_visual_candidates",
        ["selected_candidate_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_campaigns_current_visual_attempt",
        "campaigns",
        "campaign_visual_attempts",
        ["current_visual_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", type_="check"
    )
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', "
        "'copy_rewrite', 'image_generation', 'visual_planner', "
        "'visual_quality_check')",
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
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', "
        "'copy_rewrite', 'image_generation')",
    )

    op.drop_constraint(
        "fk_campaigns_current_visual_attempt", "campaigns", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_visual_attempts_selected_candidate",
        "campaign_visual_attempts",
        type_="foreignkey",
    )
    op.drop_table("campaign_visual_candidates")
    op.drop_table("campaign_visual_attempts")
    op.drop_index("ix_campaigns_current_visual_attempt_id", table_name="campaigns")
    op.drop_column("campaigns", "current_visual_attempt_id")
    op.drop_column("campaigns", "visual_recipe_json")
    op.drop_constraint(
        "ck_campaigns_visual_creation_mode", "campaigns", type_="check"
    )
    op.drop_column("campaigns", "visual_creation_mode")

    op.drop_constraint("ck_campaigns_status", "campaigns", type_="check")
    op.create_check_constraint(
        "ck_campaigns_status",
        "campaigns",
        "status in ('draft', 'brief_complete', 'concepts_ready', "
        "'concept_selected', 'queued', 'generating', 'ready', "
        "'partial_failed', 'failed')",
    )
