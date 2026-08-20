from decimal import Decimal
from typing import Protocol

from app.content.concepts import ConceptDraft
from app.content.context import CopyContext
from app.content.copy import CaptionSet, ReelConcept


class LlmUsage:
    """Tokens, latency and cost of the most recent provider call, if any."""

    __slots__ = (
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "cost_usd",
        "model",
    )

    def __init__(
        self,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
        cost_usd: Decimal | None = None,
        model: str | None = None,
    ) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd
        self.model = model


class ContentProvider(Protocol):
    """
    Everything that writes Persian campaign text.

    Campaign services talk only to this protocol. OpenRouter lives behind an
    implementation selected by `CONTENT_PROVIDER` (spec §23).
    """

    name: str
    model: str | None

    async def build_concepts(self, ctx: CopyContext) -> list[ConceptDraft]: ...

    async def build_captions(self, ctx: CopyContext) -> CaptionSet: ...

    async def build_story_ideas(self, ctx: CopyContext) -> list[str]: ...

    async def build_primary_cta(self, ctx: CopyContext) -> str: ...

    async def build_hashtags(self, ctx: CopyContext) -> str: ...

    async def build_reel_concept(self, ctx: CopyContext) -> ReelConcept: ...

    async def build_subheadline(self, ctx: CopyContext) -> str: ...

    async def rewrite_text(
        self,
        ctx: CopyContext,
        *,
        intent: str,
        current: str,
        field: str,
    ) -> str: ...

    def consume_usage(self) -> LlmUsage | None: ...
