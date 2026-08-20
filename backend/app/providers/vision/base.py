from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.providers.llm.base import LlmUsage


@dataclass(frozen=True, slots=True)
class InputQuality:
    status: str
    reasons: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True, slots=True)
class RecipeProposal:
    style_id: str
    template_id: str
    title_fa: str
    description_fa: str
    scene_direction: str
    text_safe_area: str
    identity_constraints: tuple[str, ...] = ()
    warning_fa: str = ""


@dataclass(frozen=True, slots=True)
class PlannerResult:
    product_type: str
    visual_identity: tuple[str, ...]
    identity_constraints: tuple[str, ...]
    unsuitable_style_ids: tuple[str, ...]
    unsuitable_template_ids: tuple[str, ...]
    input_quality: InputQuality
    recommended_recipes: tuple[RecipeProposal, ...]
    forbidden_claims: tuple[str, ...] = ()
    usage: LlmUsage | None = None


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


@dataclass(frozen=True, slots=True)
class QualityReport:
    candidates: tuple[CandidateQuality, ...]
    usage: LlmUsage | None = None


@dataclass(frozen=True, slots=True)
class PlannerContext:
    product_name: str
    description: str | None
    brand_name: str | None
    price_text: str | None
    audience: str | None
    objective: str
    visual_style: str
    concept_title_fa: str
    concept_headline_fa: str
    concept_visual_direction: str
    recipe: dict = field(default_factory=dict)


class VisualPlanner(Protocol):
    name: str
    model: str | None

    async def plan_recipes(
        self, image: bytes, context: PlannerContext
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
