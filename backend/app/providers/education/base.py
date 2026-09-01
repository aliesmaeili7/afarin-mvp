"""
The Educational Agent contract.

One call in, one image prompt out. Unlike the advertising Creative Agent this
takes no image: an educational post is idea-led, not product-photo-led.

The image model paints the finished poster, including any wording the teacher
already wrote. There is no overlay copy, no CTA, and no quality scorer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.providers.llm.base import LlmUsage
from app.providers.vision.base import LlmCallTrace, llm_usage_dict

__all__ = [
    "EducationalAgent",
    "EducationalAgentContext",
    "EducationalPostResult",
    "EducationalTheme",
    "llm_usage_dict",
]


@dataclass(frozen=True, slots=True)
class EducationalTheme:
    """
    Style memory only: how a series of posts should *feel*.

    Palette, material, mood, lighting, motifs. Never layout, never fonts, never
    CTA/badge/price chrome, never the lesson of the post this came from.
    """

    name_suggestion: str
    primary_colors: tuple[str, ...]
    secondary_colors: tuple[str, ...]
    illustration_style: str
    mood: str
    lighting: str
    shape_language: str
    decorative_motifs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name_suggestion": self.name_suggestion,
            "primary_colors": list(self.primary_colors),
            "secondary_colors": list(self.secondary_colors),
            "illustration_style": self.illustration_style,
            "mood": self.mood,
            "lighting": self.lighting,
            "shape_language": self.shape_language,
            "decorative_motifs": list(self.decorative_motifs),
        }


@dataclass(frozen=True, slots=True)
class EducationalPostResult:
    language: str
    final_prompt: str
    theme: EducationalTheme
    theme_style_notes: str | None = None
    safety_notes: str | None = None
    usage: LlmUsage | None = None
    llm_trace: LlmCallTrace | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "final_prompt": self.final_prompt,
            "theme": self.theme.as_dict(),
            "theme_style_notes": self.theme_style_notes,
            "safety_notes": self.safety_notes,
        }


@dataclass(frozen=True, slots=True)
class EducationalAgentContext:
    """
    Everything the agent gets. Note what is absent: no subject, grade, tone,
    audience, title, overlay copy or font list. Those would turn this into the
    form we chose not to build, or into an ad layout.
    """

    user_prompt: str
    #: A builtin or saved theme to stay consistent with, else None to design one.
    selected_theme: dict[str, Any] | None = None
    aspect: str = "1:1"
    extra: dict[str, Any] = field(default_factory=dict)


class EducationalAgent(Protocol):
    name: str
    model: str | None

    async def create_post(
        self,
        context: EducationalAgentContext,
        *,
        correction: str | None = None,
    ) -> EducationalPostResult: ...
