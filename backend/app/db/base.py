import uuid
from datetime import datetime
from typing import Any, Literal, overload

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.enums import sql_in


class Base(DeclarativeBase):
    # Fetch server-generated values (ids, timestamps) with RETURNING on the
    # INSERT itself. Without this the ORM defers them to a lazy SELECT, which
    # under asyncio raises MissingGreenlet the moment a response is serialized.
    __mapper_args__ = {"eager_defaults": True}


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def created_timestamp() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def updated_timestamp() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


@overload
def user_fk(
    *, nullable: Literal[True] = True, index: bool = True
) -> Mapped[uuid.UUID | None]: ...


@overload
def user_fk(
    *, nullable: Literal[False], index: bool = True
) -> Mapped[uuid.UUID]: ...


def user_fk(*, nullable: bool = True, index: bool = True) -> Any:
    """
    The owning user, as the Supabase JWT `sub` claim.

    This references profiles.user_id rather than auth.users.id. Supabase's auth
    schema is owned by supabase_admin, which holds USAGE and REFERENCES without
    grant option, so no least-privilege role can ever be granted enough to build
    a cross-schema foreign key. Anchoring on profiles keeps full referential
    integrity and cascade deletes inside the schema we own; profiles.user_id is
    the single point that mirrors an auth user.
    """
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=nullable,
        index=index,
    )


def json_column(name: str) -> Mapped[dict]:
    return mapped_column(
        JSONB, name=name, nullable=False, server_default=text("'{}'::jsonb")
    )


def enum_check(
    table: str, column: str, values: tuple[str, ...], *, nullable: bool = False
) -> CheckConstraint:
    """CHECK keeping `column` inside `values`, tolerating NULL when allowed."""
    inside = f"{column} in ({sql_in(values)})"
    expression = f"{column} is null or {inside}" if nullable else inside
    return CheckConstraint(expression, name=f"ck_{table}_{column}")


def text_column(*, nullable: bool = True) -> Mapped[str | None]:
    return mapped_column(String, nullable=nullable)
