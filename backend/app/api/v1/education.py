"""
Educational content endpoints.

Every route here requires a signed-in user except `GET /themes`, which stays
open so a visitor can browse built-in themes before the signup gate. No
educational row is ever created for an anonymous caller.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Response
from sqlalchemy import select

from app.core import messages
from app.core.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.errors import invalid
from app.db.models import EducationalPost, EducationalTheme
from app.db.session import get_sessionmaker
from app.schemas.education import (
    MAX_PROMPT_CHARS,
    CreateEducationalPostIn,
    EducationalPostOut,
    EducationalPostStatusOut,
    EducationalPostSummaryOut,
    EducationalThemeListOut,
    EducationalThemeOut,
    RenameEducationalThemeIn,
    SaveEducationalThemeIn,
)
from app.services.education import generate as education_generate
from app.services.education import themes as theme_service
from app.services.education.ownership import (
    get_owned_post,
    get_owned_theme,
    require_education_user,
)
from app.services.identity.service import get_or_create_profile

router = APIRouter(prefix="/api/education", tags=["education"])

logger = logging.getLogger(__name__)

_TERMINAL = ("ready", "failed")


@router.post("/posts", response_model=EducationalPostOut)
async def create_post(
    body: CreateEducationalPostIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> EducationalPost:
    """
    The one and only creation point, and it is always authenticated.

    A visitor may type the prompt and pick a theme first; that lives in the
    browser until they sign in, so there is no anonymous row to adopt later.
    """
    user_id = require_education_user(principal)
    prompt = (body.user_prompt or "").strip()
    if not prompt:
        raise invalid(messages.EDUCATION_PROMPT_REQUIRED)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise invalid(messages.EDUCATION_PROMPT_TOO_LONG)

    # Educational can be the first thing a new account ever opens, and
    # ownership hangs off profiles.user_id, so the profile must exist first.
    await get_or_create_profile(session, user_id, principal.email)

    theme = await theme_service.resolve_theme(
        session,
        user_id=user_id,
        theme_id=body.theme_id,
        builtin_id=body.builtin_theme_id,
    )
    post = EducationalPost(
        user_id=user_id,
        user_prompt=prompt,
        selected_theme_id=body.theme_id,
        selected_builtin_theme_id=body.builtin_theme_id,
        status="queued",
        # Holds the selected theme until generation replaces it with the
        # effective one, so the agent input survives a restart.
        theme_json=theme or {},
    )
    session.add(post)
    await session.flush()
    return post


@router.get("/posts", response_model=list[EducationalPostSummaryOut])
async def list_posts(
    session: SessionDep, principal: PrincipalDep
) -> list[EducationalPost]:
    user_id = require_education_user(principal)
    rows = await session.scalars(
        select(EducationalPost)
        .where(EducationalPost.user_id == user_id)
        .order_by(EducationalPost.created_at.desc())
    )
    return list(rows)


@router.get("/posts/{post_id}", response_model=EducationalPostOut)
async def get_post(
    post_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> EducationalPost:
    return await get_owned_post(session, principal, post_id)


@router.get("/posts/{post_id}/status", response_model=EducationalPostStatusOut)
async def get_post_status(
    post_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
    background: BackgroundTasks,
) -> EducationalPostStatusOut:
    """
    Advances the run, mirroring the advertising poll so the progress UI is
    reusable. Stub providers run inline; live providers hand off to a worker so
    the poller can keep reporting.
    """
    post = await get_owned_post(session, principal, post_id)
    if post.status in _TERMINAL:
        return _status(post)

    if post.status == "generating":
        return _status(post)

    if settings.image_provider != "stub":
        post.status = "generating"
        post.updated_at = datetime.now(UTC)
        await session.flush()
        await session.commit()
        background.add_task(_run_background, post.id)
        return _status(post, stage="planning", percent=15)

    try:
        await education_generate.run_generation(session, post)
    except Exception:
        logger.exception("educational generation failed")
    return _status(post)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> Response:
    post = await get_owned_post(session, principal, post_id)
    await session.delete(post)
    await session.flush()
    return Response(status_code=204)


@router.get("/themes", response_model=EducationalThemeListOut)
async def list_themes(
    session: SessionDep, principal: PrincipalDep
) -> EducationalThemeListOut:
    """
    Open to anonymous callers on purpose: the theme picker should render on the
    creation page before sign-in. Saved themes simply come back empty.
    """
    saved: list[EducationalTheme] = []
    if principal.user_id is not None:
        saved = await theme_service.list_saved_themes(session, principal.user_id)
    return EducationalThemeListOut(
        builtin=theme_service.builtin_catalog(),
        saved=[EducationalThemeOut.model_validate(row) for row in saved],
    )


@router.post("/themes", response_model=EducationalThemeOut)
async def save_theme(
    body: SaveEducationalThemeIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> EducationalTheme:
    """
    Saves the post's visual system for reuse.

    `sanitize_theme` strips the topic, headline and image prompt, so what is
    stored is a look rather than a copy of the post.
    """
    user_id = require_education_user(principal)
    await get_or_create_profile(session, user_id, principal.email)
    post = await get_owned_post(session, principal, body.post_id)
    if not post.theme_json:
        raise invalid(messages.EDUCATION_THEME_NOT_SAVEABLE)

    theme_json = theme_service.sanitize_theme(post.theme_json)
    name = (body.name or "").strip() or theme_service.theme_name_of(
        post.theme_json, post.headline or "تم آموزشی"
    )
    if not name:
        raise invalid(messages.EDUCATION_THEME_NAME_REQUIRED)
    theme_json["name"] = name

    row = EducationalTheme(
        user_id=user_id, name=name, theme_json=theme_json, source="user"
    )
    session.add(row)
    await session.flush()
    return row


@router.patch("/themes/{theme_id}", response_model=EducationalThemeOut)
async def rename_theme(
    theme_id: uuid.UUID,
    body: RenameEducationalThemeIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> EducationalTheme:
    theme = await get_owned_theme(session, principal, theme_id)
    name = (body.name or "").strip()
    if not name:
        raise invalid(messages.EDUCATION_THEME_NAME_REQUIRED)
    theme.name = name
    stored = dict(theme.theme_json or {})
    stored["name"] = name
    theme.theme_json = stored
    theme.updated_at = datetime.now(UTC)
    await session.flush()
    return theme


@router.delete("/themes/{theme_id}", status_code=204)
async def delete_theme(
    theme_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> Response:
    theme = await get_owned_theme(session, principal, theme_id)
    await session.delete(theme)
    await session.flush()
    return Response(status_code=204)


async def _run_background(post_id: uuid.UUID) -> None:
    async with get_sessionmaker()() as session:
        try:
            post = await session.get(EducationalPost, post_id)
            if post is None:
                return
            await education_generate.run_generation(session, post)
            await session.commit()
        except Exception:
            logger.exception("background educational generation failed")
            await session.rollback()
            async with get_sessionmaker()() as failed:
                post = await failed.get(EducationalPost, post_id)
                if post is not None and post.status not in _TERMINAL:
                    post.status = "failed"
                    post.error_message = messages.GENERATION_FAILED
                    post.updated_at = datetime.now(UTC)
                await failed.commit()


def _status(
    post: EducationalPost,
    *,
    stage: str | None = None,
    percent: int | None = None,
) -> EducationalPostStatusOut:
    if post.status == "ready":
        return EducationalPostStatusOut(
            post_id=post.id,
            status=post.status,
            stage=None,
            percent=100,
            message_fa=None,
        )
    if post.status == "failed":
        return EducationalPostStatusOut(
            post_id=post.id,
            status=post.status,
            stage=None,
            percent=0,
            message_fa=post.error_message or messages.GENERATION_FAILED,
        )
    return EducationalPostStatusOut(
        post_id=post.id,
        status=post.status,
        stage=stage or "planning",
        percent=percent if percent is not None else 5,
        message_fa=messages.QUEUED,
    )
