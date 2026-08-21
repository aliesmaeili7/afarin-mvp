"""creative director planner result and parallel generation jobs

Revision ID: e1f4a8c2d9b0
Revises: d8c2f4a1b0e3
Create Date: 2026-08-21 00:20:00.000000

Stores the multimodal Creative Director snapshot on the campaign and lets
copy + image jobs be active at the same time.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f4a8c2d9b0"
down_revision: str | None = "d8c2f4a1b0e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "planner_result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_index("uq_generation_jobs_active", table_name="generation_jobs")
    op.create_index(
        "uq_generation_jobs_active",
        "generation_jobs",
        ["campaign_id", "job_type"],
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
        postgresql_where=sa.text(
            "status in ('queued', 'processing') "
            "AND job_type in ('campaign_generation', 'image_generation')"
        ),
    )
    op.drop_column("campaigns", "planner_result_json")
