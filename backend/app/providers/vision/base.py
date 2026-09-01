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
class QualityContext:
    product_name: str
    template_id: str | None = None
    identity_constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TextSafeArea:
    position: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"position": self.position, "description": self.description}


@dataclass(frozen=True, slots=True)
class VisualPlan:
    template_id: str | None
    scene: str
    composition: str
    camera: str
    lighting: str
    palette: str
    product_role: str
    human_or_pose: str | None
    text_safe_area: TextSafeArea

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "scene": self.scene,
            "composition": self.composition,
            "camera": self.camera,
            "lighting": self.lighting,
            "palette": self.palette,
            "product_role": self.product_role,
            "human_or_pose": self.human_or_pose,
            "text_safe_area": self.text_safe_area.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ConceptIdentity:
    must_preserve: tuple[str, ...]
    must_not_generate: tuple[str, ...]

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "must_preserve": list(self.must_preserve),
            "must_not_generate": list(self.must_not_generate),
        }


@dataclass(frozen=True, slots=True)
class ConceptCopy:
    on_image_headline: str
    on_image_secondary: str | None
    feed_caption: str
    story_text: str
    cta: str
    hashtags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "on_image_headline": self.on_image_headline,
            "on_image_secondary": self.on_image_secondary,
            "feed_caption": self.feed_caption,
            "story_text": self.story_text,
            "cta": self.cta,
            "hashtags": list(self.hashtags),
        }


@dataclass(frozen=True, slots=True)
class CampaignStrategy:
    core_message: str
    audience_takeaway: str
    tone: str

    def as_dict(self) -> dict[str, str]:
        return {
            "core_message": self.core_message,
            "audience_takeaway": self.audience_takeaway,
            "tone": self.tone,
        }


@dataclass(frozen=True, slots=True)
class CreativeImage:
    concept_title: str
    creative_angle: str
    visual_plan: VisualPlan
    identity: ConceptIdentity
    final_prompt: str
    copy: ConceptCopy

    def as_dict(self) -> dict[str, Any]:
        return {
            "concept_title": self.concept_title,
            "creative_angle": self.creative_angle,
            "visual_plan": self.visual_plan.as_dict(),
            "identity": self.identity.as_dict(),
            "final_prompt": self.final_prompt,
            "copy": self.copy.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class CreativeAgentResult:
    product_summary: str
    campaign_strategy: CampaignStrategy
    images: tuple[CreativeImage, ...]
    usage: LlmUsage | None = None
    llm_trace: LlmCallTrace | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_summary": self.product_summary,
            "campaign_strategy": self.campaign_strategy.as_dict(),
            "images": [item.as_dict() for item in self.images],
        }


@dataclass(frozen=True, slots=True)
class CreativeAgentContext:
    product_name: str
    description: str | None
    brand_name: str | None
    price_text: str | None
    audience: str | None
    objective: str
    visual_style: str
    requested_image_count: int
    template_id: str | None = None
    template_semantics: dict = field(default_factory=dict)
    visual_instruction: str | None = None
    catalog_digest: str = ""


class CreativeAgent(Protocol):
    name: str
    model: str | None

    async def create_campaign(
        self,
        image: bytes,
        context: CreativeAgentContext,
        *,
        correction: str | None = None,
    ) -> CreativeAgentResult: ...

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: QualityContext,
    ) -> QualityReport: ...
