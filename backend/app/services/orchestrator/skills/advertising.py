"""Advertising skill: internal Campaign + Creative Agent. References, not copies."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import get_settings
from app.core.errors import ApiError
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
from app.providers.image import get_image_provider
from app.services.campaigns import jobs as job_records
from app.services.campaigns.creative import generate_candidates
from app.services.campaigns.crop import CropRect
from app.services.campaigns.product_media import save_crop
from app.services.orchestrator.activity import set_activity_phase
from app.services.orchestrator.edit_text import wants_rendered_ad_as_product
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

        async def on_progress(stage: str) -> None:
            if stage == "visual":
                await set_activity_phase(
                    context.assistant_message.id, "generating_image"
                )
            elif stage == "finalizing":
                await set_activity_phase(
                    context.assistant_message.id, "finalizing"
                )

        provider_name = get_image_provider().name
        try:
            usage = await generate_candidates(
                session, campaign, job, source="custom", on_progress=on_progress
            )
        except Exception as error:
            job_records.mark_image_failed(job, error, provider=provider_name)
            if isinstance(error, ApiError) and error.message_fa in (
                messages.INPUT_QUALITY_NEEDS_FIX,
                messages.CREATIVE_ATTEMPTS_EXHAUSTED,
            ):
                campaign.status = "brief_complete"
            else:
                campaign.status = "partial_failed"
            campaign.updated_at = datetime.now(UTC)
            await session.commit()
            raise
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
            empty = RuntimeError("advertising produced no images")
            job_records.mark_image_failed(job, empty, provider=provider_name)
            campaign.status = "partial_failed"
            campaign.updated_at = datetime.now(UTC)
            await session.commit()
            raise empty

        job_records.mark_image_succeeded(
            job,
            usage,
            provider=provider_name,
            output=dict(job.input_json or {}),
        )

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
    """
    Prefer the original product photo, not a rendered ad.

    The rendered campaign image is used only when the user explicitly asks
    to treat it as the product photo.
    """
    attachment = (context.user_message.metadata_json or {}).get("attachment") or {}
    path = attachment.get("storage_path")
    mime = str(attachment.get("mime_type") or "image/png")
    if isinstance(path, str) and path:
        data = await _download(path)
        if data:
            return data, mime

    if wants_rendered_ad_as_product(context.user_text):
        rendered = await _load_referenced_artifact_bytes(session, context)
        if rendered[0]:
            return rendered

    from_campaign = await _load_campaign_product_bytes(session, context)
    if from_campaign[0]:
        return from_campaign

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


async def _load_referenced_artifact_bytes(
    session: AsyncSession, context: SkillContext
) -> tuple[bytes | None, str]:
    ids = list(context.reference_artifact_ids or context.source_artifact_ids)
    if not ids:
        return None, ""
    rows = list(
        await session.scalars(
            select(ChatArtifact).where(
                ChatArtifact.conversation_id == context.conversation.id,
                ChatArtifact.id.in_(ids),
                ChatArtifact.status == "ready",
            )
        )
    )
    for row in rows:
        if row.storage_path:
            data = await _download(row.storage_path)
            if data:
                return data, row.mime_type or "image/jpeg"
    return None, ""


async def _load_campaign_product_bytes(
    session: AsyncSession, context: SkillContext
) -> tuple[bytes | None, str]:
    campaign_ids: list[uuid.UUID] = []
    ids = list(context.reference_artifact_ids or context.source_artifact_ids)
    rows: list[ChatArtifact] = []
    if ids:
        rows = list(
            await session.scalars(
                select(ChatArtifact).where(
                    ChatArtifact.conversation_id == context.conversation.id,
                    ChatArtifact.id.in_(ids),
                    ChatArtifact.status == "ready",
                )
            )
        )
    if not rows:
        rows = list(
            await session.scalars(
                select(ChatArtifact)
                .where(
                    ChatArtifact.conversation_id == context.conversation.id,
                    ChatArtifact.status == "ready",
                    ChatArtifact.artifact_type == "image",
                )
                .order_by(ChatArtifact.created_at.desc())
                .limit(8)
            )
        )
    for row in rows:
        meta = row.metadata_json or {}
        raw = meta.get("campaign_id") or (
            meta.get("source_domain_id")
            if meta.get("source_domain") == "advertising"
            or meta.get("skill") == "advertising"
            else None
        )
        if not raw:
            continue
        try:
            campaign_ids.append(uuid.UUID(str(raw)))
        except (ValueError, TypeError):
            continue
    for campaign_id in campaign_ids:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None or campaign.user_id != context.user_id:
            continue
        if campaign.product_id is None:
            continue
        images = list(
            await session.scalars(
                select(ProductImage)
                .where(ProductImage.product_id == campaign.product_id)
                .order_by(ProductImage.is_primary.desc())
            )
        )
        for image in images:
            data = await _download(image.storage_path)
            if data:
                return data, "image/png"
    return None, ""


async def _download(path: str) -> bytes | None:
    ref = parse(path)
    if ref is None:
        return None
    return await get_storage().download(ref)
