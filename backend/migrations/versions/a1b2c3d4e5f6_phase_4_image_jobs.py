"""phase 4 image generation jobs

Revision ID: a1b2c3d4e5f6
Revises: c3a91e07f2b4
Create Date: 2026-08-20 16:40:00.000000

Empty-scene generation is a first-class job type, and the one-active-job
index is scoped to campaign and image work so copy rewrite cannot collide.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c3a91e07f2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_generation_jobs_job_type", "generation_jobs", type_="check")
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', "
        "'copy_rewrite', 'image_generation')",
    )
    op.drop_index("uq_generation_jobs_active", table_name="generation_jobs")
    op.create_index(
        "uq_generation_jobs_active",
        "generation_jobs",
        ["campaign_id"],
        unique=True,
        postgresql_where=sa.text(
            "status in ('queued', 'processing') "
            "AND job_type in ('campaign_generation', 'image_generation')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_generation_jobs_active", table_name="generation_jobs")
    op.create_index(
        "uq_generation_jobs_active",
        "generation_jobs",
        ["campaign_id"],
        unique=True,
        postgresql_where=sa.text("status in ('queued', 'processing')"),
    )
    op.drop_constraint("ck_generation_jobs_job_type", "generation_jobs", type_="check")
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', 'copy_rewrite')",
    )
