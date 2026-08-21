from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmInputQuality(_Strict):
    status: Literal["ok", "needs_fix"]
    reasons: list[str] = Field(default_factory=list)


class LlmDirection(_Strict):
    title_fa: str = Field(min_length=1, max_length=80)
    description_fa: str = Field(min_length=1, max_length=240)
    angle: str = Field(min_length=1, max_length=80)
    headline_fa: str = Field(min_length=1, max_length=80)
    visual_direction: str = Field(min_length=1, max_length=240)
    style_id: str = Field(min_length=1, max_length=64)
    template_id: str = Field(min_length=1, max_length=64)
    identity_constraints: list[str] = Field(default_factory=list)
    warning_fa: str = ""
    image_direction: str = Field(min_length=1, max_length=400)
    background_prompt: str = Field(min_length=1, max_length=400)
    text_safe_area: str = Field(min_length=1, max_length=32)


class LlmPlannerResult(_Strict):
    product_visual_analysis: str = Field(min_length=1, max_length=400)
    product_type: str = Field(min_length=1, max_length=80)
    visual_identity: list[str]
    identity_constraints: list[str]
    unsuitable_style_ids: list[str]
    unsuitable_template_ids: list[str]
    input_quality: LlmInputQuality
    directions: list[LlmDirection] = Field(min_length=3, max_length=3)
    forbidden_claims: list[str]


class LlmCandidateQuality(_Strict):
    slot: int = Field(ge=1, le=3)
    hard_failed: bool
    reasons: list[str]
    identity_recognizable: bool
    no_random_text_or_logos: bool
    no_severe_artifacts: bool
    no_unwanted_duplicates: bool
    ad_composition: bool
    text_safe_space: bool


class LlmQualityReport(_Strict):
    candidates: list[LlmCandidateQuality] = Field(min_length=1, max_length=3)
