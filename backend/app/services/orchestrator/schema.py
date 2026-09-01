"""Strict Orchestrator JSON schema. No chain-of-thought fields."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Route = Literal[
    "advertising",
    "education",
    "general_image",
    "image_edit",
    "general_chat",
    "clarify",
    "unsupported",
]
ChatLanguage = Literal["fa", "en"]

ORCHESTRATOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "route": {
            "type": "string",
            "enum": [
                "advertising",
                "education",
                "general_image",
                "image_edit",
                "general_chat",
                "clarify",
                "unsupported",
            ],
        },
        "reply_language": {"type": "string", "enum": ["fa", "en"]},
        "artifact_language": {
            "anyOf": [
                {"type": "string", "enum": ["fa", "en"]},
                {"type": "null"},
            ]
        },
        "assistant_preamble": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "assistant_message": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "generation_instruction": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "edit_instruction": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "target_aspect_ratio": {
            "anyOf": [
                {"type": "string", "enum": ["1:1", "4:5", "9:16"]},
                {"type": "null"},
            ]
        },
        "requested_image_count": {
            "anyOf": [{"type": "integer", "enum": [1, 3]}, {"type": "null"}]
        },
    },
    "required": [
        "route",
        "reply_language",
        "artifact_language",
        "assistant_preamble",
        "assistant_message",
        "needs_clarification",
        "clarification_question",
        "generation_instruction",
        "edit_instruction",
        "target_aspect_ratio",
        "requested_image_count",
    ],
}


class OrchestratorDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    route: Route
    reply_language: ChatLanguage
    artifact_language: ChatLanguage | None = None
    assistant_preamble: str | None = None
    assistant_message: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    generation_instruction: str | None = None
    edit_instruction: str | None = None
    target_aspect_ratio: Literal["1:1", "4:5", "9:16"] | None = None
    requested_image_count: Literal[1, 3] | None = None
    orchestrator_called: bool = Field(default=True, exclude=True)
