"""Chat-only general image. Uses GENERAL_IMAGE_MODEL, never Seedream."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.providers.image import get_image_provider
from app.providers.image.base import ImageRequest
from app.services.orchestrator.skills.base import (
    ProducedImage,
    SkillContext,
    SkillResult,
)
from app.services.orchestrator.texts import ack_for
from app.services.storage import chat_artifact_key, get_storage
from app.services.storage.paths import StorageRef


class GeneralImageSkill:
    name = "general_image"

    async def execute(
        self, session: AsyncSession, context: SkillContext
    ) -> SkillResult:
        settings = get_settings()
        prompt = (context.generation_instruction or context.user_text).strip()
        if not prompt:
            prompt = "a simple illustration"
        result = await get_image_provider().generate(
            ImageRequest(
                prompt=prompt,
                aspect_ratio="1:1",
                resolution=settings.image_resolution,
                model=settings.general_image_model_resolved,
            )
        )
        token = uuid.uuid4().hex[:12]
        ref = StorageRef(
            bucket=settings.bucket_product_images,
            key=chat_artifact_key(context.conversation.id, token, "jpg"),
        )
        await get_storage().upload(
            ref, result.content, result.media_type or "image/jpeg"
        )
        return SkillResult(
            images=[
                ProducedImage(
                    storage_path=ref.to_path(),
                    mime_type=result.media_type or "image/jpeg",
                    aspect_ratio="1:1",
                    metadata={"skill": self.name},
                )
            ],
            assistant_content=ack_for("general_image", context.reply_language),
            metadata={"skill": self.name},
        )
