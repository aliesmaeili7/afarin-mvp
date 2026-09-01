"""Chat activity_phase writes. UX telemetry only — never fail generation."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import type_coerce, update
from sqlalchemy.dialects.postgresql import JSONB

from app.db.models import ChatMessage
from app.db.session import get_sessionmaker
from app.services.orchestrator.schema import Route

logger = logging.getLogger(__name__)

ACTIVITY_PHASES = frozenset(
    {
        "preparing_advertising",
        "preparing_education",
        "preparing_image",
        "generating_image",
        "finalizing",
    }
)

PREPARING_FOR_ROUTE: dict[str, str] = {
    "advertising": "preparing_advertising",
    "education": "preparing_education",
    "general_image": "preparing_image",
}


def preparing_phase_for(route: Route | str) -> str:
    return PREPARING_FOR_ROUTE.get(str(route), "preparing_image")


async def set_activity_phase(assistant_id: uuid.UUID, phase: str) -> None:
    """
    Merge only `activity_phase` into metadata_json while status is generating.

    Uses JSONB `||` so concurrent keys (route, campaign ids, retry flags)
    are preserved. Failures are logged and swallowed.
    """
    if phase not in ACTIVITY_PHASES:
        logger.warning("ignored unknown chat activity_phase=%s", phase)
        return
    try:
        async with get_sessionmaker()() as session:
            patch = type_coerce({"activity_phase": phase}, JSONB)
            await session.execute(
                update(ChatMessage)
                .where(
                    ChatMessage.id == assistant_id,
                    ChatMessage.metadata_json["status"].as_string() == "generating",
                )
                .values(metadata_json=ChatMessage.metadata_json.op("||")(patch))
            )
            await session.commit()
    except Exception:
        logger.exception("chat activity_phase=%s persist failed", phase)
