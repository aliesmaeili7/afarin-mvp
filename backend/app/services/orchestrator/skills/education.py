"""Education skill: internal EducationalPost, existing educational generator."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EducationalPost
from app.services.education import generate as education_generate
from app.services.orchestrator.activity import set_activity_phase
from app.services.orchestrator.skills.base import (
    ProducedImage,
    SkillContext,
    SkillResult,
)
from app.services.orchestrator.texts import ack_for


class EducationSkill:
    name = "education"

    async def execute(
        self, session: AsyncSession, context: SkillContext
    ) -> SkillResult:
        theme = _theme_snapshot(context.active_theme)
        post = EducationalPost(
            user_id=context.user_id,
            user_prompt=context.user_text,
            status="queued",
            theme_json=theme,
        )
        session.add(post)
        await session.flush()

        async def on_image_start() -> None:
            await set_activity_phase(
                context.assistant_message.id, "generating_image"
            )

        await education_generate.run_generation(
            session, post, on_image_start=on_image_start
        )
        if post.status != "ready" or not post.image_storage_path:
            raise RuntimeError(post.error_message or "educational generation failed")

        caption = _caption_from(post)
        return SkillResult(
            images=[
                ProducedImage(
                    storage_path=post.image_storage_path,
                    mime_type="image/jpeg",
                    aspect_ratio="1:1",
                    metadata={
                        "skill": self.name,
                        "educational_post_id": str(post.id),
                    },
                    caption=caption,
                )
            ],
            assistant_content=_assistant_copy(context, caption),
            metadata={"skill": self.name, "educational_post_id": str(post.id)},
        )


def _theme_snapshot(active: dict | None) -> dict:
    if not active:
        return {}
    style = active.get("style_json")
    if isinstance(style, dict) and style:
        payload = dict(style)
        if active.get("name"):
            payload.setdefault("name", active["name"])
        return payload
    return {}


def _caption_from(post: EducationalPost) -> str | None:
    agent = post.agent_json or {}
    result = agent.get("result") if isinstance(agent, dict) else None
    if not isinstance(result, dict):
        result = agent if isinstance(agent, dict) else {}
    for key in ("caption", "instagram_caption", "overlay_caption"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if post.headline:
        return post.headline
    return None


def _assistant_copy(context: SkillContext, caption: str | None) -> str:
    lead = ack_for("education", context.reply_language)
    if caption:
        return f"{lead}\n\n{caption}".strip()
    return lead
