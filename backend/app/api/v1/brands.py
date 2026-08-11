import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.core import messages
from app.core.deps import PrincipalDep, SessionDep
from app.core.errors import forbidden, invalid, not_found
from app.db.models import Brand
from app.schemas.domain import BrandOut
from app.schemas.requests import BrandIn

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("", response_model=list[BrandOut])
async def list_brands(session: SessionDep, principal: PrincipalDep) -> list[Brand]:
    """
    The Brand Kit, now persistent across devices.

    Anonymous visitors have no Brand Kit: a brand only becomes durable once
    there is an account to attach it to.
    """
    if not principal.is_authenticated:
        return []
    rows = await session.scalars(
        select(Brand)
        .where(Brand.user_id == principal.user_id)
        .order_by(Brand.created_at.desc())
    )
    return list(rows)


@router.post("", response_model=BrandOut)
async def create_brand(
    body: BrandIn, session: SessionDep, principal: PrincipalDep
) -> Brand:
    if not body.name or not body.name.strip():
        raise invalid(messages.BRAND_NAME_REQUIRED)

    brand = Brand(user_id=principal.user_id, **_fields(body))
    session.add(brand)
    await session.flush()
    return brand


@router.patch("/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> Brand:
    brand = await session.scalar(select(Brand).where(Brand.id == brand_id))
    if brand is None:
        raise not_found(messages.BRAND_NOT_FOUND)
    if brand.user_id is not None and brand.user_id != principal.user_id:
        raise forbidden(messages.BRAND_FORBIDDEN)
    if not body.name or not body.name.strip():
        raise invalid(messages.BRAND_NAME_REQUIRED)

    for field, value in _fields(body).items():
        setattr(brand, field, value)
    brand.updated_at = datetime.now(UTC)

    await session.flush()
    return brand


def _fields(body: BrandIn) -> dict[str, str | None]:
    data = body.model_dump()
    data["name"] = data["name"].strip()
    return data
