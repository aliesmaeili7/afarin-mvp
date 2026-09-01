"""
Ownership for the chat domain.

Conversations are authenticated-only. Unknown ids and foreign ids both 404 so
holding someone else's conversation UUID is not enough to learn that it exists.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.deps import Principal
from app.core.errors import forbidden, not_found
from app.db.models import ChatConversation


def require_chat_user(principal: Principal) -> uuid.UUID:
    if principal.user_id is None:
        raise forbidden(messages.CHAT_SIGN_IN_REQUIRED)
    return principal.user_id


async def get_owned_chat_conversation(
    session: AsyncSession, principal: Principal, conversation_id: uuid.UUID
) -> ChatConversation:
    user_id = require_chat_user(principal)
    conversation = await session.scalar(
        select(ChatConversation).where(ChatConversation.id == conversation_id)
    )
    if conversation is None or conversation.user_id != user_id:
        raise not_found(messages.CHAT_NOT_FOUND)
    return conversation
