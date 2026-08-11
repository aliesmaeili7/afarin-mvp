import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_timestamp, pk, updated_timestamp, user_fk


class Profile(Base):
    """Spec §22 profiles. Credit columns exist but carry no logic until Phase 7."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = pk()
    # The Supabase auth user id. Not a foreign key: the auth schema cannot be
    # referenced by a least-privilege role (see app/db/base.py:user_fk). Unique,
    # so every other table can hang its ownership off this column instead.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    locale: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'fa'")
    )
    credit_balance_cached: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    free_campaigns_remaining: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    # Phase 1 handed its seeded sample campaign to the first account; here each
    # new profile gets its own copy exactly once.
    sample_seeded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class AnonymousSession(Base):
    """
    Pre-signup ownership.

    The token itself lives only in an HttpOnly cookie; we keep its SHA-256 hash
    so a database dump cannot be replayed against the API.
    """

    __tablename__ = "anonymous_sessions"

    id: Mapped[uuid.UUID] = pk()
    token_hash: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    claimed_by_user_id: Mapped[uuid.UUID | None] = user_fk(index=False)
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = created_timestamp()
    last_seen_at: Mapped[datetime] = created_timestamp()
