import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import Settings, get_settings
from app.core.errors import forbidden
from app.core.security import (
    AuthenticatedUser,
    InvalidToken,
    hash_anonymous_token,
    verify_access_token,
)
from app.db.models import AnonymousSession
from app.db.session import get_session


@dataclass(frozen=True, slots=True)
class Principal:
    """
    Who is making this request.

    Exactly one of these is set. A Bearer token always wins over the anonymous
    cookie, so a signed-in seller never accidentally acts as their old
    anonymous self.
    """

    user_id: uuid.UUID | None
    anonymous_session_id: uuid.UUID | None
    email: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    def require_user(self) -> uuid.UUID:
        if self.user_id is None:
            raise forbidden(messages.SIGN_IN_REQUIRED)
        return self.user_id


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def current_user(request: Request) -> AuthenticatedUser | None:
    token = _bearer_token(request)
    if token is None:
        return None
    try:
        return verify_access_token(token)
    except InvalidToken as error:
        raise forbidden(messages.SIGN_IN_REQUIRED) from error


async def _anonymous_session(
    request: Request, session: AsyncSession, settings: Settings
) -> AnonymousSession | None:
    """
    Reads the HttpOnly cookie. JavaScript never sees this value, which is why
    it is safe for it to grant access to an unclaimed campaign.
    """
    token = request.cookies.get(settings.anon_cookie_name)
    if not token:
        return None

    row = await session.scalar(
        select(AnonymousSession).where(
            AnonymousSession.token_hash == hash_anonymous_token(token)
        )
    )
    if row is None:
        return None

    row.last_seen_at = datetime.now(UTC)
    return row


async def get_principal(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    user = current_user(request)
    if user is not None:
        return Principal(
            user_id=uuid.UUID(user.user_id),
            anonymous_session_id=None,
            email=user.email,
        )

    anonymous = await _anonymous_session(request, session, settings)
    return Principal(
        user_id=None,
        anonymous_session_id=anonymous.id if anonymous else None,
    )


async def db_session(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[AsyncSession]:
    yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
