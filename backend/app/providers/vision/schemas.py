from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmInputQuality(_Strict):
    status: Literal["ok", "needs_fix"]
    reasons: list[str] = Field(default_factory=list)


class LlmCropBox(_Strict):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class LlmReferenceAnalysis(_Strict):
    cleanliness: Literal[
        "clean",
        "peripheral_ui",
        "isolatable_subject",
        "overlapping_contamination",
        "ambiguous",
    ]
    product_visibility: Literal["excellent", "good", "weak", "unusable"]
    screenshot_ui_present: bool
    watermark_present: bool
    multiple_products: bool
    person_present: bool
    useful_context_present: bool
    contamination_description: list[str] = Field(default_factory=list)
    reference_strategy: Literal[
        "direct_crop",
        "tighter_crop",
        "subject_cutout_neutral",
        "preserve_context_crop",
        "needs_user_action",
    ]
    recommended_crop: LlmCropBox
    has_recommended_crop: bool
    preserve_context_reason: str = ""
    blocking_reasons: list[str] = Field(default_factory=list)
    brief_image_mismatch: bool = False


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
    compatibility: Literal["preferred", "allowed", "discouraged"] = "allowed"


class LlmPlannerResult(_Strict):
    product_visual_analysis: str = Field(min_length=1, max_length=400)
    product_type: str = Field(min_length=1, max_length=80)
    visual_identity: list[str]
    identity_constraints: list[str]
    unsuitable_style_ids: list[str]
    unsuitable_template_ids: list[str]
    input_quality: LlmInputQuality
    reference_analysis: LlmReferenceAnalysis
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
    identity_quality: int = Field(ge=1, le=5)
    style_adherence: int = Field(ge=1, le=5)
    template_adherence: int = Field(ge=1, le=5)
    composition_quality: int = Field(ge=1, le=5)
    visual_attractiveness: int = Field(ge=1, le=5)
    commercial_usefulness: int = Field(ge=1, le=5)
    text_safe_space_quality: int = Field(ge=1, le=5)


class LlmQualityReport(_Strict):
    candidates: list[LlmCandidateQuality] = Field(min_length=1, max_length=3)


class LlmIdentityFeature(_Strict):
    feature: str = Field(min_length=1, max_length=160)
    importance: Literal["critical", "important"]


class LlmExistingTextAndGraphics(_Strict):
    preserve: bool
    instructions: str = Field(default="", max_length=240)


class LlmArchitectProduct(_Strict):
    role_in_scene: str = Field(min_length=1, max_length=240)
    identity_priority: list[LlmIdentityFeature] = Field(default_factory=list)
    existing_text_and_graphics: LlmExistingTextAndGraphics


class LlmArchitectScene(_Strict):
    environment: str = Field(min_length=1, max_length=240)
    story_or_context: str = Field(min_length=1, max_length=240)
    foreground: str = Field(min_length=1, max_length=240)
    background: str = Field(min_length=1, max_length=240)
    props: list[str] = Field(default_factory=list)


class LlmCandidateComposition(_Strict):
    camera: str = Field(min_length=1, max_length=240)
    lens_feel: str = Field(min_length=1, max_length=160)
    product_scale: str = Field(min_length=1, max_length=160)
    product_position: str = Field(min_length=1, max_length=160)
    human_or_pose: str = ""
    depth: str = Field(min_length=1, max_length=160)


class LlmArchitectLighting(_Strict):
    direction: str = Field(min_length=1, max_length=160)
    quality: str = Field(min_length=1, max_length=160)
    mood: str = Field(min_length=1, max_length=160)


class LlmColorAndMaterial(_Strict):
    palette: str = Field(min_length=1, max_length=240)
    material_treatment: str = Field(min_length=1, max_length=240)


class LlmTypographySafeArea(_Strict):
    position: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)


class LlmArchitectOutput(_Strict):
    aspect_ratio: str = Field(min_length=1, max_length=16)
    format: str = Field(min_length=1, max_length=80)


class LlmProductPlacement(_Strict):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    rotation_degrees: float = Field(ge=-45.0, le=45.0)
    contact_surface: str = ""
    shadow_direction: str = ""
    shadow_softness: str = ""


class LlmArchitectCandidate(_Strict):
    slot: Literal[1, 2, 3]
    intention: Literal["safe", "editorial", "bold"]
    creative_intent: str = Field(min_length=1, max_length=240)
    product: LlmArchitectProduct
    scene: LlmArchitectScene
    composition: LlmCandidateComposition
    lighting: LlmArchitectLighting
    color_and_material: LlmColorAndMaterial
    typography_safe_area: LlmTypographySafeArea
    must_preserve: list[str] = Field(default_factory=list)
    must_not_generate: list[str] = Field(default_factory=list)
    render_strategy: Literal["reference_transform", "preserved_product_composite"]
    has_product_placement: bool
    product_placement: LlmProductPlacement
    output: LlmArchitectOutput
    final_prompt: str = Field(min_length=1, max_length=1200)


class LlmPromptArchitectResult(_Strict):
    reference_summary: str = Field(min_length=1, max_length=400)
    candidates: list[LlmArchitectCandidate] = Field(min_length=3, max_length=3)
