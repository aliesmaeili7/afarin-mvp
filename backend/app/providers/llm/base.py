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


def merge_llm_usage(
    first: LlmUsage | None, second: LlmUsage | None
) -> LlmUsage | None:
    """
    Totals two calls, so a retry's cost is added to the first attempt's rather
    than replacing it. Lives here beside LlmUsage because both the advertising
    and educational agents need it.
    """
    if first is None:
        return second
    if second is None:
        return first
    cost = None
    if first.cost_usd is not None or second.cost_usd is not None:
        cost = (first.cost_usd or Decimal("0")) + (second.cost_usd or Decimal("0"))
    return LlmUsage(
        prompt_tokens=_add_int(first.prompt_tokens, second.prompt_tokens),
        completion_tokens=_add_int(
            first.completion_tokens, second.completion_tokens
        ),
        latency_ms=_add_int(first.latency_ms, second.latency_ms),
        cost_usd=cost,
        model=second.model or first.model,
    )


def _add_int(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)


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
