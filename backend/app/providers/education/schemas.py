"""
Strict shape of the Educational Agent's single JSON response.

The image model receives only `final_prompt`. Everything else is for Afarin:
language, optional notes, and a style-only theme for later reuse.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmEducationalTheme(_Strict):
    """Visual semantics only. No fonts, treatments, CTAs or layout slots."""

    name_suggestion: str = Field(min_length=1, max_length=60)
    primary_colors: list[str] = Field(min_length=1, max_length=6)
    secondary_colors: list[str] = Field(default_factory=list, max_length=6)
    illustration_style: str = Field(min_length=1, max_length=240)
    mood: str = Field(min_length=1, max_length=160)
    lighting: str = Field(min_length=1, max_length=160)
    shape_language: str = Field(min_length=1, max_length=240)
    decorative_motifs: list[str] = Field(default_factory=list, max_length=12)


class LlmEducationalPostResult(_Strict):
    language: Literal["fa", "en"]
    # Schema allows headroom; validate.py enforces the real 800-char ceiling so
    # an over-long prompt becomes a correctable error rather than a hard parse
    # failure that wastes the whole call.
    final_prompt: str = Field(min_length=1, max_length=1200)
    theme: LlmEducationalTheme
    theme_style_notes: str | None = Field(default=None, max_length=400)
    safety_notes: str | None = Field(default=None, max_length=400)
