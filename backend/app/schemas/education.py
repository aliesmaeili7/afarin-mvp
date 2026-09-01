"""
Educational request and response bodies.

Note what the create body does NOT contain: no subject, grade, audience, tone,
title or style. One prompt and an optional theme is the whole input.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

MAX_PROMPT_CHARS = 2000


class CreateEducationalPostIn(BaseModel):
    user_prompt: str
    #: A saved theme row, or a builtin id. Both optional: no theme means the
    #: agent designs one.
    theme_id: uuid.UUID | None = None
    builtin_theme_id: str | None = None


class SaveEducationalThemeIn(BaseModel):
    post_id: uuid.UUID
    #: Defaults to the agent's own name_suggestion.
    name: str | None = None


class RenameEducationalThemeIn(BaseModel):
    name: str


class EducationalThemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source: str
    theme_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EducationalThemeListOut(BaseModel):
    builtin: list[dict[str, Any]]
    saved: list[EducationalThemeOut]


class EducationalPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_prompt: str
    selected_theme_id: uuid.UUID | None
    selected_builtin_theme_id: str | None
    language: str | None
    headline: str | None
    status: str
    error_message: str | None
    image_storage_path: str | None
    agent_json: dict[str, Any]
    theme_json: dict[str, Any]
    render_spec_json: dict[str, Any]
    wall_time_ms: int | None
    created_at: datetime
    updated_at: datetime


class EducationalPostSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    headline: str | None
    status: str
    language: str | None
    image_storage_path: str | None
    created_at: datetime


class EducationalPostStatusOut(BaseModel):
    post_id: uuid.UUID
    status: str
    stage: str | None
    percent: int
    message_fa: str | None
