"""product image crop metadata

Revision ID: b7e4c1a90d12
Revises: a1b2c3d4e5f6
Create Date: 2026-08-20 18:00:00.000000

Original uploads stay untouched. Crop rectangles and JPEG derivatives live
on product_images so AdCanvas can composite a product, not a screenshot.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e4c1a90d12"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_images",
        sa.Column(
            "crop_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "product_images",
        sa.Column("crop_storage_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_images", "crop_storage_path")
    op.drop_column("product_images", "crop_json")
