import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    created_timestamp,
    pk,
    text_column,
    updated_timestamp,
    user_fk,
)


class Product(Base):
    """Spec §22 products."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID | None] = user_fk()
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Blank until the seller fills the brief; the row is created with the
    # campaign's first upload, mirroring the mock's ensureProduct.
    name: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    description: Mapped[str | None] = text_column()
    price_text: Mapped[str | None] = text_column()
    main_benefit: Mapped[str | None] = text_column()
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class ProductImage(Base):
    """Spec §22 product_images."""

    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_timestamp()
