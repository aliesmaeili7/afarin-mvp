"""Chat-owned image edit. Reference-conditioned generation, not inpainting."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ChatArtifact
from app.providers.image import get_image_provider
from app.providers.image.base import ImageRequest
from app.services.orchestrator.activity import set_activity_phase
from app.services.orchestrator.edit_text import (
    quoted_strings,
    theme_line,
)
from app.services.orchestrator.skills.base import (
    ProducedImage,
    SkillContext,
    SkillResult,
)
from app.services.orchestrator.texts import ack_for
from app.services.storage import chat_artifact_key, get_storage, parse
from app.services.storage.paths import StorageRef

logger = logging.getLogger(__name__)

_PRESERVE = (
    "Edit the attached reference image. This is reference-conditioned "
    "generation, not mask inpainting. Apply only the requested change. "
    "Preserve composition, subject, and other text unless asked otherwise."
)


class ImageEditSkill:
    name = "image_edit"

    async def execute(
        self, session: AsyncSession, context: SkillContext
    ) -> SkillResult:
        source_bytes, source_meta = await _load_source(session, context)
        if not source_bytes:
            raise RuntimeError("image_edit needs a reference image")

        settings = get_settings()
        instruction = (context.edit_instruction or context.user_text).strip()
        prompt = _prompt_for(instruction, context)
        aspect = context.target_aspect_ratio or source_meta.get("aspect_ratio") or "1:1"
        if aspect not in ("1:1", "4:5", "9:16"):
            aspect = "1:1"

        await set_activity_phase(context.assistant_message.id, "generating_image")
        result = await get_image_provider().generate(
            ImageRequest(
                prompt=prompt,
                aspect_ratio=aspect,
                resolution=settings.image_resolution,
                references=(source_bytes,),
                model=settings.chat_image_edit_model_resolved,
            )
        )
        logger.info(
            "chat image_edit conversation_id=%s user_message_id=%s "
            "assistant_message_id=%s source_artifact_id=%s model=%s "
            "latency_ms=%s cost_usd=%s",
            context.conversation.id,
            context.user_message.id,
            context.assistant_message.id,
            next(iter(source_meta.get("source_artifact_ids") or []), None),
            result.usage.model,
            result.usage.latency_ms,
            result.usage.cost_usd,
        )

        token = uuid.uuid4().hex[:12]
        ref = StorageRef(
            bucket=settings.bucket_product_images,
            key=chat_artifact_key(context.conversation.id, token, "jpg"),
        )
        await get_storage().upload(
            ref, result.content, result.media_type or "image/jpeg"
        )
        lineage = {
            "skill": self.name,
            "source_artifact_ids": source_meta.get("source_artifact_ids") or [],
            "edit_instruction": instruction,
            "generation": source_meta.get("generation", 1),
            "usage": {
                "model": result.usage.model,
                "latency_ms": result.usage.latency_ms,
                "cost_usd": (
                    str(result.usage.cost_usd)
                    if result.usage.cost_usd is not None
                    else None
                ),
            },
        }
        if source_meta.get("source_domain"):
            lineage["source_domain"] = source_meta["source_domain"]
        if source_meta.get("source_domain_id"):
            lineage["source_domain_id"] = source_meta["source_domain_id"]
        if source_meta.get("source_message_id"):
            lineage["source_message_id"] = source_meta["source_message_id"]

        return SkillResult(
            images=[
                ProducedImage(
                    storage_path=ref.to_path(),
                    mime_type=result.media_type or "image/jpeg",
                    aspect_ratio=aspect,
                    metadata=lineage,
                )
            ],
            assistant_content=ack_for("image_edit", context.reply_language),
            metadata={"skill": self.name, **lineage},
        )


def _prompt_for(instruction: str, context: SkillContext) -> str:
    parts = [_PRESERVE, instruction]
    quotes = quoted_strings(instruction)
    if quotes:
        joined = " | ".join(quotes)
        parts.append(
            "Use this on-image text exactly, with no translation, "
            f"paraphrase, or spelling change: {joined}"
        )
    if context.artifact_language == "en":
        parts.append("On-image text should be English.")
    elif context.artifact_language == "fa":
        parts.append("On-image text should be Persian. Do not transliterate.")
    theme = theme_line(context.user_text, context.active_theme)
    if theme:
        parts.append(theme)
    return "\n".join(part for part in parts if part)


async def _load_source(
    session: AsyncSession, context: SkillContext
) -> tuple[bytes | None, dict[str, Any]]:
    wanted = list(context.source_artifact_ids or context.reference_artifact_ids)
    for artifact_id in wanted:
        artifact = await session.get(ChatArtifact, artifact_id)
        if (
            artifact is None
            or artifact.conversation_id != context.conversation.id
            or artifact.status != "ready"
            or artifact.artifact_type != "image"
            or not artifact.storage_path
        ):
            continue
        data = await _download(artifact.storage_path)
        if not data:
            continue
        meta = dict(artifact.metadata_json or {})
        source_gen = meta.get("generation")
        generation = int(source_gen) + 1 if isinstance(source_gen, int) else 2
        domain = meta.get("source_domain") or meta.get("skill")
        domain_id = (
            meta.get("source_domain_id")
            or meta.get("campaign_id")
            or meta.get("educational_post_id")
        )
        if domain not in ("advertising", "education", "general_image"):
            domain = None
            domain_id = None
        return data, {
            "aspect_ratio": artifact.aspect_ratio,
            "source_artifact_ids": [str(artifact.id)],
            "generation": generation,
            "source_domain": domain,
            "source_domain_id": domain_id,
        }

    path = context.source_attachment_path
    if isinstance(path, str) and path:
        data = await _download(path)
        if data:
            return data, {
                "aspect_ratio": context.target_aspect_ratio or "1:1",
                "source_artifact_ids": [],
                "generation": 1,
                "source_message_id": str(context.source_message_id)
                if context.source_message_id
                else None,
            }
    return None, {}


async def _download(path: str) -> bytes | None:
    ref = parse(path)
    if ref is None:
        return None
    return await get_storage().download(ref)
