"""chat phase d: allow 9:16 chat artifacts

Revision ID: d4a9c1e2b7f0
Revises: c5f8a2d01b34
Create Date: 2026-09-01 23:20:00.000000

Conversational story reframes persist as 9:16. Advertising/education
domain assets are unchanged.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4a9c1e2b7f0"
down_revision: str | None = "c5f8a2d01b34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_chat_artifacts_aspect_ratio", "chat_artifacts", type_="check"
    )
    op.create_check_constraint(
        "ck_chat_artifacts_aspect_ratio",
        "chat_artifacts",
        "aspect_ratio is null or aspect_ratio in ('1:1', '4:5', '9:16')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_chat_artifacts_aspect_ratio", "chat_artifacts", type_="check"
    )
    op.create_check_constraint(
        "ck_chat_artifacts_aspect_ratio",
        "chat_artifacts",
        "aspect_ratio is null or aspect_ratio in ('1:1', '4:5')",
    )
