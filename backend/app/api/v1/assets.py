from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, PrincipalDep, SessionDep
from app.core.errors import ApiError
from app.db.models import Brand, Campaign
from app.schemas.requests import ResolveAssetsIn
from app.services.campaigns.ownership import get_owned_campaign
from app.services.storage import is_public, parse, resolve_paths
from app.services.storage.paths import owner_scope

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.post("/resolve", response_model=dict[str, str | None])
async def resolve(
    body: ResolveAssetsIn, session: SessionDep, principal: PrincipalDep
) -> dict[str, str | None]:
    """
    Turns storage paths into short-lived signed URLs.

    Batched deliberately: a results page shows five assets at once, and one
    round trip per image would visibly stagger the reveal.

    Ownership is re-derived from each object key rather than trusted, so holding
    a path is not sufficient to read the object behind it.
    """
    if not body.paths:
        return {}

    allowed: list[str] = []
    denied: dict[str, str | None] = {}

    for path in body.paths:
        if is_public(path):
            allowed.append(path)
            continue
        ref = parse(path)
        scope = owner_scope(ref) if ref else None
        if scope is None or not await _may_read(session, principal, scope):
            denied[path] = None
            continue
        allowed.append(path)

    return {**denied, **await resolve_paths(allowed)}


async def _may_read(session: AsyncSession, principal: Principal, scope) -> bool:
    if scope.kind == "campaign":
        try:
            await get_owned_campaign(session, principal, scope.id)
        except ApiError:
            return False
        return True

    brand = await session.scalar(select(Brand).where(Brand.id == scope.id))
    if brand is None:
        return False
    if brand.user_id is not None:
        return brand.user_id == principal.user_id
    # An unclaimed brand is readable by whoever owns a campaign pointing at it.
    linked = await session.scalar(
        select(Campaign.id).where(Campaign.brand_id == scope.id).limit(1)
    )
    if linked is None:
        return False
    try:
        await get_owned_campaign(session, principal, linked)
    except ApiError:
        return False
    return True
