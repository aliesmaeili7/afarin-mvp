"""prompt architect jobs, clean reference path, attempt architect json

Revision ID: f2a9b7c4e1d8
Revises: e1f4a8c2d9b0
Create Date: 2026-08-24 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a9b7c4e1d8"
down_revision: str | None = "e1f4a8c2d9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_images",
        sa.Column("clean_reference_storage_path", sa.String(), nullable=True),
    )
    op.add_column(
        "campaign_visual_attempts",
        sa.Column(
            "prompt_architect_json",
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
        "'prompt_architect', 'visual_quality_check')",
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
        "'visual_quality_check')",
    )
    op.drop_column("campaign_visual_attempts", "prompt_architect_json")
    op.drop_column("product_images", "clean_reference_storage_path")
