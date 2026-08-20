import uuid

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.cookies import clear_anonymous_cookie, set_anonymous_cookie
from app.core.deps import Principal, PrincipalDep, SessionDep, SettingsDep
from app.core.security import hash_anonymous_token
from app.db.models import AnonymousSession
from app.schemas.domain import SessionOut, SessionUserOut
from app.services.identity import service as identity

router = APIRouter(prefix="/api/session", tags=["session"])


async def ensure_anonymous_owner(
    request: Request,
    response: Response,
    session: AsyncSession,
    principal: Principal,
    settings: Settings,
) -> Principal:
    """
    Guarantees the caller has some owner before creating a campaign.

    Idempotent: an existing valid cookie is reused rather than replaced, because
    the frontend cannot read the cookie to check whether it already has one.
    A signed-in caller gets a profile row if this is their first write, so
    campaigns.user_id cannot miss profiles.user_id.
    """
    if principal.is_authenticated:
        await identity.get_or_create_profile(
            session, principal.require_user(), principal.email
        )
        return principal

    if principal.anonymous_session_id is not None:
        return principal

    token = request.cookies.get(settings.anon_cookie_name)
    if token:
        existing = await session.scalar(
            select(AnonymousSession).where(
                AnonymousSession.token_hash == hash_anonymous_token(token)
            )
        )
        if existing is not None:
            return Principal(user_id=None, anonymous_session_id=existing.id)

    created, raw_token = await identity.create_anonymous_session(session)
    set_anonymous_cookie(response, settings, raw_token)
    return Principal(user_id=None, anonymous_session_id=created.id)


@router.post("/anonymous", status_code=204)
async def start_anonymous_session(
    request: Request,
    response: Response,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
) -> Response:
    """Mints an anonymous session. The token is returned only via Set-Cookie."""
    await ensure_anonymous_owner(request, response, session, principal, settings)
    response.status_code = 204
    return response


@router.post("/adopt", response_model=SessionOut)
async def adopt(
    request: Request,
    response: Response,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
) -> SessionOut:
    """
    Called immediately after sign-in.

    Creates the profile if this is a first sign-in, transfers anything the
    anonymous visitor made to the account, and clears the spent cookie.
    """
    user_id = principal.require_user()
    profile = await identity.get_or_create_profile(session, user_id, principal.email)

    anonymous_id = await _anonymous_session_id(request, session, settings)
    if anonymous_id is not None:
        await identity.adopt_anonymous_session(session, anonymous_id, user_id)
        clear_anonymous_cookie(response, settings)

    return _session_payload(profile)


@router.get("/me", response_model=SessionOut | None)
async def me(
    session: SessionDep,
    principal: PrincipalDep,
) -> SessionOut | None:
    if not principal.is_authenticated:
        return None
    profile = await identity.get_or_create_profile(
        session, principal.require_user(), principal.email
    )
    return _session_payload(profile)


async def _anonymous_session_id(
    request: Request, session: AsyncSession, settings: Settings
) -> uuid.UUID | None:
    token = request.cookies.get(settings.anon_cookie_name)
    if not token:
        return None
    row = await session.scalar(
        select(AnonymousSession).where(
            AnonymousSession.token_hash == hash_anonymous_token(token)
        )
    )
    return row.id if row else None


def _session_payload(profile) -> SessionOut:
    return SessionOut(
        user=SessionUserOut(
            id=profile.user_id,
            email=profile.email or "",
            display_name=profile.display_name,
            locale=profile.locale,
            free_campaigns_remaining=profile.free_campaigns_remaining,
        ),
        # The real bearer token lives in the Supabase client on the frontend;
        # this field exists only to satisfy the Phase 1 Session shape.
        access_token="",
    )
