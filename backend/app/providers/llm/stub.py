from app.content import concepts as concept_fixtures
from app.content import copy as copy_fixtures
from app.content.concepts import ConceptDraft
from app.content.context import CopyContext
from app.content.copy import CaptionSet, ReelConcept
from app.providers.llm.base import LlmUsage


class StubContentProvider:
    """
    Deterministic Persian fixtures, no model call.

    Used by the test suite and local development without an API key. The words
    stay identical to Phase 1 so swapping CONTENT_PROVIDER cannot change fixture
    campaigns.
    """

    name = "stub"
    model: str | None = None

    async def build_concepts(self, ctx: CopyContext) -> list[ConceptDraft]:
        return concept_fixtures.build_concepts(ctx)

    async def build_captions(self, ctx: CopyContext) -> CaptionSet:
        return copy_fixtures.build_captions(ctx)

    async def build_story_ideas(self, ctx: CopyContext) -> list[str]:
        return copy_fixtures.build_story_ideas(ctx)

    async def build_primary_cta(self, ctx: CopyContext) -> str:
        return copy_fixtures.build_primary_cta(ctx)

    async def build_hashtags(self, ctx: CopyContext) -> str:
        return copy_fixtures.build_hashtags(ctx)

    async def build_reel_concept(self, ctx: CopyContext) -> ReelConcept:
        return copy_fixtures.build_reel_concept(ctx)

    async def build_subheadline(self, ctx: CopyContext) -> str:
        return concept_fixtures.build_subheadline(ctx)

    async def rewrite_text(
        self,
        ctx: CopyContext,
        *,
        intent: str,
        current: str,
        field: str,
    ) -> str:
        text = current.strip()
        if intent == "shorter":
            first = text.split("\n", 1)[0].strip()
            if first and first != text:
                return first
            return text[: max(12, len(text) // 2)].rstrip()
        if intent == "informal":
            return text if "😊" in text else f"{text}\nخوشحال می‌شیم کمکت کنیم 😊"
        if intent == "stronger_cta":
            if field == "cta":
                return "همین حالا سفارش بده"
            return f"{text}\nهمین حالا سفارش بده 👇"
        if intent == "new_headline":
            return f"{ctx.product_name}، انتخاب هوشمندانه‌تر"
        if intent == "more_luxury":
            return f"مجموعه‌ای منتخب\n{text}"
        return text

    def consume_usage(self) -> LlmUsage | None:
        return None
