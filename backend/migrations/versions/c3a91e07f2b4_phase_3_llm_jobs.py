"""phase 3 llm observability

Revision ID: c3a91e07f2b4
Revises: 9f2b7c4d5e10
Create Date: 2026-08-20 12:20:00.000000

Concept generation and copy rewrite are now first-class job types, and every
LLM call records tokens, latency and provider cost. Credits are still out of
scope.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a91e07f2b4"
down_revision: str | None = "9f2b7c4d5e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_generation_jobs_job_type", "generation_jobs", type_="check")
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation', 'concept_generation', 'copy_rewrite')",
    )
    op.add_column(
        "generation_jobs", sa.Column("prompt_tokens", sa.Integer(), nullable=True)
    )
    op.add_column(
        "generation_jobs", sa.Column("completion_tokens", sa.Integer(), nullable=True)
    )
    op.add_column(
        "generation_jobs", sa.Column("latency_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "generation_jobs",
        sa.Column("actual_cost_usd", sa.Numeric(precision=12, scale=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "actual_cost_usd")
    op.drop_column("generation_jobs", "latency_ms")
    op.drop_column("generation_jobs", "completion_tokens")
    op.drop_column("generation_jobs", "prompt_tokens")
    op.drop_constraint("ck_generation_jobs_job_type", "generation_jobs", type_="check")
    op.create_check_constraint(
        "ck_generation_jobs_job_type",
        "generation_jobs",
        "job_type in ('campaign_generation')",
    )
