"""Advertising skill: internal Campaign + Creative Agent. References, not copies."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import (
    Campaign,
    CampaignCopy,
    CampaignVisualCandidate,
    ChatArtifact,
    ChatMessage,
    GenerationJob,
    Product,
    ProductImage,
)
from app.services.campaigns.creative import generate_candidates
from app.services.campaigns.crop import CropRect
from app.services.campaigns.product_media import save_crop
from app.services.orchestrator.skills.base import (
    ProducedImage,
    SkillContext,
    SkillResult,
)
from app.services.orchestrator.texts import ack_for
from app.services.storage import get_storage, parse, product_image_key, validate_upload
from app.services.storage.paths import StorageRef


class AdvertisingSkill:
    name = "advertising"

    async def execute(
        self, session: AsyncSession, context: SkillContext
    ) -> SkillResult:
        image_bytes, mime = await _load_product_bytes(session, context)
        if not image_bytes:
            raise RuntimeError("advertising needs a product image")

        product = Product(user_id=context.user_id, name="")
        session.add(product)
        await session.flush()

        campaign = Campaign(
            user_id=context.user_id,
            product_id=product.id,
            objective="sell_product",
            visual_style="modern",
            visual_instruction=context.user_text,
            requested_image_count=context.requested_image_count
            if context.requested_image_count in (1, 3)
            else 1,
            status="queued",
            is_free_campaign=True,
        )
        session.add(campaign)
        await session.flush()

        settings = get_settings()
        extension = validate_upload(
            image_bytes, mime or "image/png", settings.max_upload_bytes
        )
        row = ProductImage(
            product_id=product.id,
            storage_path="",
            is_primary=True,
        )
        session.add(row)
        await session.flush()
        ref = StorageRef(
            bucket=settings.bucket_product_images,
            key=product_image_key(campaign.id, row.id, extension),
        )
        await get_storage().upload(ref, image_bytes, mime or "image/png")
        row.storage_path = ref.to_path()
        await save_crop(
            session,
            campaign,
            row,
            CropRect(0.0, 0.0, 1.0, 1.0),
            original_bytes=image_bytes,
        )

        job = GenerationJob(
            campaign_id=campaign.id,
            user_id=context.user_id,
            job_type="campaign_generation",
            status="processing",
            started_at=datetime.now(UTC),
            input_json={
                "source": "chat",
                "conversation_id": str(context.conversation.id),
            },
        )
        session.add(job)
        await session.flush()

        await generate_candidates(session, campaign, job, source="custom")
        await session.refresh(campaign)

        attempt_id = campaign.current_visual_attempt_id
        candidates: list[CampaignVisualCandidate] = []
        if attempt_id is not None:
            candidates = list(
                await session.scalars(
                    select(CampaignVisualCandidate)
                    .where(
                        CampaignVisualCandidate.attempt_id == attempt_id,
                        CampaignVisualCandidate.hidden.is_(False),
                        CampaignVisualCandidate.hard_failed.is_(False),
                    )
                    .order_by(CampaignVisualCandidate.slot)
                )
            )

        copies = list(
            await session.scalars(
                select(CampaignCopy).where(CampaignCopy.campaign_id == campaign.id)
            )
        )
        captions = [
            item.content
            for item in copies
            if item.copy_type in ("caption_persuasive", "cta") and item.content
        ]
        caption = "\n".join(captions[:2]) if captions else None

        images = [
            ProducedImage(
                storage_path=item.storage_path,
                mime_type="image/jpeg",
                aspect_ratio="4:5",
                metadata={
                    "skill": self.name,
                    "campaign_id": str(campaign.id),
                    "visual_attempt_id": str(item.attempt_id),
                    "candidate_id": str(item.id),
                },
                caption=caption if index == 0 else None,
            )
            for index, item in enumerate(candidates)
        ]
        if not images:
            raise RuntimeError("advertising produced no images")

        attempt_ids = [str(item.attempt_id) for item in candidates]
        return SkillResult(
            images=images,
            assistant_content=_assistant_copy(context, caption),
            metadata={
                "skill": self.name,
                "campaign_id": str(campaign.id),
                "visual_attempt_ids": attempt_ids,
            },
        )


def _assistant_copy(context: SkillContext, caption: str | None) -> str:
    lead = ack_for("advertising", context.reply_language)
    if caption:
        return f"{lead}\n\n{caption}".strip()
    return lead


async def _load_product_bytes(
    session: AsyncSession, context: SkillContext
) -> tuple[bytes | None, str]:
    attachment = (context.user_message.metadata_json or {}).get("attachment") or {}
    path = attachment.get("storage_path")
    mime = str(attachment.get("mime_type") or "image/png")
    if isinstance(path, str) and path:
        data = await _download(path)
        if data:
            return data, mime

    if context.reference_artifact_ids:
        rows = list(
            await session.scalars(
                select(ChatArtifact).where(
                    ChatArtifact.conversation_id == context.conversation.id,
                    ChatArtifact.id.in_(context.reference_artifact_ids),
                    ChatArtifact.status == "ready",
                )
            )
        )
        for row in rows:
            if row.storage_path:
                data = await _download(row.storage_path)
                if data:
                    return data, row.mime_type or "image/jpeg"

    recent = list(
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == context.conversation.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
    )
    for item in recent:
        att = (item.metadata_json or {}).get("attachment") or {}
        path = att.get("storage_path")
        if isinstance(path, str) and path:
            data = await _download(path)
            if data:
                return data, str(att.get("mime_type") or "image/png")
    return None, ""


async def _download(path: str) -> bytes | None:
    ref = parse(path)
    if ref is None:
        return None
    return await get_storage().download(ref)
