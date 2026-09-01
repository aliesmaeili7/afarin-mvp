"""
Ownership for the educational domain.

Simpler than advertising on purpose: both educational tables carry a NOT NULL
`user_id`, so there is no anonymous-session branch to consider. The two-message
convention is kept, though, because knowing an id should never be enough to
learn whether it exists.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.deps import Principal
from app.core.errors import forbidden, not_found
from app.db.models import EducationalPost, EducationalTheme


async def get_owned_post(
    session: AsyncSession, principal: Principal, post_id: uuid.UUID
) -> EducationalPost:
    user_id = require_education_user(principal)
    post = await session.scalar(
        select(EducationalPost).where(EducationalPost.id == post_id)
    )
    if post is None:
        raise not_found(messages.EDUCATION_POST_NOT_FOUND)
    if post.user_id != user_id:
        raise forbidden(messages.EDUCATION_POST_FORBIDDEN)
    return post


async def get_owned_theme(
    session: AsyncSession, principal: Principal, theme_id: uuid.UUID
) -> EducationalTheme:
    user_id = require_education_user(principal)
    theme = await session.scalar(
        select(EducationalTheme).where(EducationalTheme.id == theme_id)
    )
    if theme is None:
        raise not_found(messages.EDUCATION_THEME_NOT_FOUND)
    if theme.user_id != user_id:
        raise forbidden(messages.EDUCATION_THEME_FORBIDDEN)
    return theme


def require_education_user(principal: Principal) -> uuid.UUID:
    """
    Educational content is authenticated-only, with its own Persian message so
    the gate reads as "sign in to make a post", not "sign in to make a campaign".
    """
    if principal.user_id is None:
        raise forbidden(messages.EDUCATION_SIGN_IN_REQUIRED)
    return principal.user_id
