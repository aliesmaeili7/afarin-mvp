import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import BRAND_ASSET_TYPES, VISUAL_STYLES
from app.db.base import (
    Base,
    created_timestamp,
    enum_check,
    json_column,
    pk,
    text_column,
    updated_timestamp,
    user_fk,
)


class Brand(Base):
    """Spec §22 brands — the Brand Kit, now persistent across devices."""

    __tablename__ = "brands"
    __table_args__ = (
        enum_check("brands", "visual_style", VISUAL_STYLES, nullable=True),
    )

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID | None] = user_fk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = text_column()
    category: Mapped[str | None] = text_column()
    instagram_handle: Mapped[str | None] = text_column()
    website: Mapped[str | None] = text_column()
    target_audience: Mapped[str | None] = text_column()
    tone: Mapped[str | None] = text_column()
    visual_style: Mapped[str | None] = text_column()
    primary_color: Mapped[str | None] = text_column()
    secondary_color: Mapped[str | None] = text_column()
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class BrandAsset(Base):
    """Spec §22 brand_assets. Logo upload itself is Phase 6; storage is ready now."""

    __tablename__ = "brand_assets"
    __table_args__ = (enum_check("brand_assets", "asset_type", BRAND_ASSET_TYPES),)

    id: Mapped[uuid.UUID] = pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict] = json_column("metadata_json")
    created_at: Mapped[datetime] = created_timestamp()
