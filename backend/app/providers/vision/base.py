from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.providers.llm.base import LlmUsage


def llm_image_ref(content: bytes, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "media_type": "image/png" if content.startswith(b"\x89PNG") else "image/jpeg",
    }


def llm_usage_dict(usage: LlmUsage | None) -> dict[str, Any] | None:
    if usage is None:
        return None
    return {
        "latency_ms": usage.latency_ms,
        "cost_usd": str(usage.cost_usd) if usage.cost_usd is not None else None,
        "model": usage.model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    }


@dataclass(frozen=True, slots=True)
class LlmCallTrace:
    """Text I/O of one vision LLM call. Images are fingerprints, never bytes."""

    name: str
    model: str | None
    system: str
    user: str
    images: tuple[dict[str, Any], ...] = ()
    output: str = ""
    usage: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "system": self.system,
            "user": self.user,
            "images": [dict(item) for item in self.images],
            "output": self.output,
            "usage": self.usage,
        }


@dataclass(frozen=True, slots=True)
class InputQuality:
    status: str
    reasons: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True, slots=True)
class CropBox:
    x: float
    y: float
    width: float
    height: float

    def as_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "width": round(self.width, 4),
            "height": round(self.height, 4),
        }


@dataclass(frozen=True, slots=True)
class ReferenceAnalysis:
    cleanliness: str = "clean"
    product_visibility: str = "good"
    screenshot_ui_present: bool = False
    watermark_present: bool = False
    multiple_products: bool = False
    person_present: bool = False
    useful_context_present: bool = False
    contamination_description: tuple[str, ...] = ()
    reference_strategy: str = "direct_crop"
    recommended_crop: CropBox | None = None
    preserve_context_reason: str = ""
    blocking_reasons: tuple[str, ...] = ()
    brief_image_mismatch: bool = False

    def as_dict(self) -> dict:
        crop = self.recommended_crop.as_dict() if self.recommended_crop else None
        return {
            "cleanliness": self.cleanliness,
            "product_visibility": self.product_visibility,
            "screenshot_ui_present": self.screenshot_ui_present,
            "watermark_present": self.watermark_present,
            "multiple_products": self.multiple_products,
            "person_present": self.person_present,
            "useful_context_present": self.useful_context_present,
            "contamination_description": list(self.contamination_description),
            "reference_strategy": self.reference_strategy,
            "recommended_crop": crop,
            "has_recommended_crop": crop is not None,
            "preserve_context_reason": self.preserve_context_reason,
            "blocking_reasons": list(self.blocking_reasons),
            "brief_image_mismatch": self.brief_image_mismatch,
        }


CLEAN_ANALYSIS = ReferenceAnalysis()


@dataclass(frozen=True, slots=True)
class PreviousDirection:
    title_fa: str
    angle: str
    style_id: str
    template_id: str


@dataclass(frozen=True, slots=True)
class CampaignDirection:
    title_fa: str
    description_fa: str
    angle: str
    headline_fa: str
    visual_direction: str
    style_id: str
    template_id: str
    identity_constraints: tuple[str, ...] = ()
    warning_fa: str = ""
    image_direction: str = ""
    background_prompt: str = ""
    text_safe_area: str = "bottom"
    compatibility: str = "allowed"

    @property
    def scene_direction(self) -> str:
        return self.image_direction


@dataclass(frozen=True, slots=True)
class PlannerResult:
    product_visual_analysis: str
    product_type: str
    visual_identity: tuple[str, ...]
    identity_constraints: tuple[str, ...]
    unsuitable_style_ids: tuple[str, ...]
    unsuitable_template_ids: tuple[str, ...]
    input_quality: InputQuality
    directions: tuple[CampaignDirection, ...]
    forbidden_claims: tuple[str, ...] = ()
    reference_analysis: ReferenceAnalysis = CLEAN_ANALYSIS
    usage: LlmUsage | None = None
    llm_trace: LlmCallTrace | None = None


@dataclass(frozen=True, slots=True)
class CandidateQuality:
    slot: int
    hard_failed: bool
    reasons: tuple[str, ...] = ()
    identity_recognizable: bool = True
    no_random_text_or_logos: bool = True
    no_severe_artifacts: bool = True
    no_unwanted_duplicates: bool = True
    ad_composition: bool = True
    text_safe_space: bool = True
    identity_quality: int = 4
    style_adherence: int = 3
    template_adherence: int = 3
    composition_quality: int = 3
    visual_attractiveness: int = 3
    commercial_usefulness: int = 3
    text_safe_space_quality: int = 3


@dataclass(frozen=True, slots=True)
class QualityReport:
    candidates: tuple[CandidateQuality, ...]
    usage: LlmUsage | None = None
    llm_trace: LlmCallTrace | None = None


@dataclass(frozen=True, slots=True)
class PlannerContext:
    product_name: str
    description: str | None
    brand_name: str | None
    price_text: str | None
    audience: str | None
    objective: str
    visual_style: str
    concept_title_fa: str = ""
    concept_headline_fa: str = ""
    concept_visual_direction: str = ""
    previous_directions: tuple[PreviousDirection, ...] = ()
    recipe: dict = field(default_factory=dict)
    crop_json: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IdentityFeature:
    feature: str
    importance: str


@dataclass(frozen=True, slots=True)
class ExistingTextAndGraphics:
    preserve: bool = False
    instructions: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"preserve": self.preserve, "instructions": self.instructions}


@dataclass(frozen=True, slots=True)
class ArchitectProduct:
    role_in_scene: str
    identity_priority: tuple[IdentityFeature, ...] = ()
    existing_text_and_graphics: ExistingTextAndGraphics = field(
        default_factory=ExistingTextAndGraphics
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "role_in_scene": self.role_in_scene,
            "identity_priority": [
                {"feature": item.feature, "importance": item.importance}
                for item in self.identity_priority
            ],
            "existing_text_and_graphics": self.existing_text_and_graphics.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ArchitectScene:
    environment: str
    story_or_context: str
    foreground: str
    background: str
    props: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "story_or_context": self.story_or_context,
            "foreground": self.foreground,
            "background": self.background,
            "props": list(self.props),
        }


@dataclass(frozen=True, slots=True)
class ArchitectComposition:
    camera: str
    lens_feel: str
    product_scale: str
    product_position: str
    human_or_pose: str
    depth: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "camera": self.camera,
            "lens_feel": self.lens_feel,
            "product_scale": self.product_scale,
            "product_position": self.product_position,
            "human_or_pose": self.human_or_pose or None,
            "depth": self.depth,
        }


@dataclass(frozen=True, slots=True)
class ArchitectLighting:
    direction: str
    quality: str
    mood: str

    def as_dict(self) -> dict[str, str]:
        return {
            "direction": self.direction,
            "quality": self.quality,
            "mood": self.mood,
        }


@dataclass(frozen=True, slots=True)
class ArchitectColorAndMaterial:
    palette: str
    material_treatment: str

    def as_dict(self) -> dict[str, str]:
        return {
            "palette": self.palette,
            "material_treatment": self.material_treatment,
        }


@dataclass(frozen=True, slots=True)
class TypographySafeArea:
    position: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"position": self.position, "description": self.description}


@dataclass(frozen=True, slots=True)
class ArchitectOutput:
    aspect_ratio: str = "4:5"
    format: str = "instagram advertisement still"

    def as_dict(self) -> dict[str, str]:
        return {"aspect_ratio": self.aspect_ratio, "format": self.format}


@dataclass(frozen=True, slots=True)
class ProductPlacement:
    x: float = 0.5
    y: float = 0.58
    width: float = 0.42
    rotation_degrees: float = 0.0
    contact_surface: str = ""
    shadow_direction: str = "down"
    shadow_softness: str = "soft"

    def as_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "rotation_degrees": self.rotation_degrees,
            "contact_surface": self.contact_surface,
            "shadow_direction": self.shadow_direction,
            "shadow_softness": self.shadow_softness,
        }


@dataclass(frozen=True, slots=True)
class ArchitectCandidate:
    slot: int
    intention: str
    creative_intent: str
    product: ArchitectProduct
    scene: ArchitectScene
    composition: ArchitectComposition
    lighting: ArchitectLighting
    color_and_material: ArchitectColorAndMaterial
    typography_safe_area: TypographySafeArea
    must_preserve: tuple[str, ...]
    must_not_generate: tuple[str, ...]
    render_strategy: str
    final_prompt: str
    has_product_placement: bool = False
    product_placement: ProductPlacement | None = None
    output: ArchitectOutput = field(default_factory=ArchitectOutput)

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "intention": self.intention,
            "creative_intent": self.creative_intent,
            "product": self.product.as_dict(),
            "scene": self.scene.as_dict(),
            "composition": self.composition.as_dict(),
            "lighting": self.lighting.as_dict(),
            "color_and_material": self.color_and_material.as_dict(),
            "typography_safe_area": self.typography_safe_area.as_dict(),
            "must_preserve": list(self.must_preserve),
            "must_not_generate": list(self.must_not_generate),
            "render_strategy": self.render_strategy,
            "has_product_placement": self.has_product_placement,
            "product_placement": (
                self.product_placement.as_dict()
                if self.product_placement is not None
                else None
            ),
            "output": self.output.as_dict(),
            "final_prompt": self.final_prompt,
        }


@dataclass(frozen=True, slots=True)
class PromptArchitectResult:
    reference_summary: str
    candidates: tuple[ArchitectCandidate, ...]
    usage: LlmUsage | None = None
    llm_trace: LlmCallTrace | None = None

    def as_dict(self) -> dict:
        return {
            "reference_summary": self.reference_summary,
            "candidates": [item.as_dict() for item in self.candidates],
        }


@dataclass(frozen=True, slots=True)
class ArchitectContext:
    product_name: str
    description: str | None
    brand_name: str | None
    audience: str | None
    objective: str
    visual_style: str
    recipe: dict
    reference_analysis: dict
    identity_constraints: tuple[str, ...] = ()
    concept_title_fa: str = ""
    concept_visual_direction: str = ""
    compatibility: str = "allowed"
    style_semantics: dict = field(default_factory=dict)
    template_semantics: dict = field(default_factory=dict)
    text_safe_area: str = "bottom"
    render_strategy: str = "reference_transform"
    render_strategy_reason: str = ""


class VisualPlanner(Protocol):
    name: str
    model: str | None

    async def plan_directions(
        self,
        image: bytes,
        context: PlannerContext,
        *,
        original: bytes | None = None,
    ) -> PlannerResult: ...

    async def check_input_quality(
        self, image: bytes, context: PlannerContext
    ) -> InputQuality: ...

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: PlannerContext,
    ) -> QualityReport: ...


class PromptArchitect(Protocol):
    name: str
    model: str | None

    async def plan_candidates(
        self,
        cleaned: bytes,
        context: ArchitectContext,
        *,
        original: bytes | None = None,
        correction: str | None = None,
    ) -> PromptArchitectResult: ...
