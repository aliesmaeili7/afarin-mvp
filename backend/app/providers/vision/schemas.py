from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    identity_quality: int = Field(ge=1, le=5)
    style_adherence: int = Field(ge=1, le=5)
    template_adherence: int = Field(ge=1, le=5)
    composition_quality: int = Field(ge=1, le=5)
    visual_attractiveness: int = Field(ge=1, le=5)
    commercial_usefulness: int = Field(ge=1, le=5)
    text_safe_space_quality: int = Field(ge=1, le=5)


class LlmQualityReport(_Strict):
    candidates: list[LlmCandidateQuality] = Field(min_length=1, max_length=3)


class LlmTextSafeArea(_Strict):
    position: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)


class LlmVisualPlan(_Strict):
    template_id: str | None = None
    scene: str = Field(min_length=1, max_length=400)
    composition: str = Field(min_length=1, max_length=400)
    camera: str = Field(min_length=1, max_length=240)
    lighting: str = Field(min_length=1, max_length=240)
    palette: str = Field(min_length=1, max_length=240)
    product_role: str = Field(min_length=1, max_length=240)
    human_or_pose: str | None = None
    text_safe_area: LlmTextSafeArea


class LlmIdentity(_Strict):
    must_preserve: list[str] = Field(default_factory=list)
    must_not_generate: list[str] = Field(default_factory=list)


class LlmConceptCopy(_Strict):
    on_image_headline: str = Field(min_length=1, max_length=80)
    on_image_secondary: str | None = None
    feed_caption: str = Field(min_length=1, max_length=800)
    story_text: str = Field(min_length=1, max_length=240)
    cta: str = Field(min_length=1, max_length=80)
    hashtags: list[str] = Field(min_length=1, max_length=12)


class LlmCampaignStrategy(_Strict):
    core_message: str = Field(min_length=1, max_length=240)
    audience_takeaway: str = Field(min_length=1, max_length=240)
    tone: str = Field(min_length=1, max_length=80)


class LlmCreativeImage(_Strict):
    concept_title: str = Field(min_length=1, max_length=80)
    creative_angle: str = Field(min_length=1, max_length=160)
    visual_plan: LlmVisualPlan
    identity: LlmIdentity
    final_prompt: str = Field(min_length=1, max_length=1200)
    copy: LlmConceptCopy


class LlmCreativeAgentResult(_Strict):
    product_summary: str = Field(min_length=1, max_length=400)
    campaign_strategy: LlmCampaignStrategy
    images: list[LlmCreativeImage] = Field(min_length=1, max_length=3)
