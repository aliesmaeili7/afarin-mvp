import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.deps import Principal
from app.core.errors import forbidden, not_found
from app.db.models import Campaign


async def get_owned_campaign(
    session: AsyncSession, principal: Principal, campaign_id: uuid.UUID
) -> Campaign:
    """
    Ownership check for every campaign endpoint (spec §27).

    A direct port of assertOwnership in the Phase 1 mock, including its two
    distinct Persian messages: an unknown id reads as "not found", someone
    else's campaign reads as "not yours". Knowing an id is never enough.
    """
    campaign = await session.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if campaign is None:
        raise not_found(messages.CAMPAIGN_NOT_FOUND)

    if campaign.user_id is not None:
        if principal.user_id is None or principal.user_id != campaign.user_id:
            raise forbidden(messages.CAMPAIGN_FORBIDDEN)
        return campaign

    if (
        campaign.anonymous_session_id is not None
        and campaign.anonymous_session_id != principal.anonymous_session_id
    ):
        raise forbidden(messages.CAMPAIGN_FORBIDDEN)

    return campaign
