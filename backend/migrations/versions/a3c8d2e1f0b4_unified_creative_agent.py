"""unified creative agent columns and job type

Revision ID: a3c8d2e1f0b4
Revises: f2a9b7c4e1d8
Create Date: 2026-08-27 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3c8d2e1f0b4"
down_revision: str | None = "f2a9b7c4e1d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "requested_image_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.add_column("campaigns", sa.Column("visual_instruction", sa.String(), nullable=True))
    op.add_column(
        "campaigns", sa.Column("selected_template_id", sa.String(), nullable=True)
    )
    op.create_check_constraint(
        "ck_campaigns_requested_image_count",
        "campaigns",
        "requested_image_count in (1, 3)",
    )
    op.add_column(
        "campaign_visual_attempts",
        sa.Column(
            "creative_agent_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", type_="check"
    )
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', "
        "'copy_rewrite', 'image_generation', 'visual_planner', "
        "'prompt_architect', 'creative_agent', 'visual_quality_check')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_generation_jobs_job_type", "generation_jobs", type_="check"
    )
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', "
        "'copy_rewrite', 'image_generation', 'visual_planner', "
        "'prompt_architect', 'visual_quality_check')",
    )
    op.drop_column("campaign_visual_attempts", "creative_agent_json")
    op.drop_constraint(
        "ck_campaigns_requested_image_count", "campaigns", type_="check"
    )
    op.drop_column("campaigns", "selected_template_id")
    op.drop_column("campaigns", "visual_instruction")
    op.drop_column("campaigns", "requested_image_count")
