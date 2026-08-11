from app.content import concepts as concept_fixtures
from app.content import copy as copy_fixtures
from app.content.concepts import ConceptDraft
from app.content.context import CopyContext
from app.content.copy import CaptionSet, ReelConcept


class StubContentProvider:
    """
    Deterministic Persian fixtures, no model call.

    This is what makes Phase 2 possible without AI: the backend genuinely owns
    and persists campaign content, while the words themselves still come from
    the same fixtures Phase 1 used.
    """

    name = "stub"

    def build_concepts(self, ctx: CopyContext) -> list[ConceptDraft]:
        return concept_fixtures.build_concepts(ctx)

    def build_captions(self, ctx: CopyContext) -> CaptionSet:
        return copy_fixtures.build_captions(ctx)

    def build_story_ideas(self, ctx: CopyContext) -> list[str]:
        return copy_fixtures.build_story_ideas(ctx)

    def build_primary_cta(self, ctx: CopyContext) -> str:
        return copy_fixtures.build_primary_cta(ctx)

    def build_hashtags(self, ctx: CopyContext) -> str:
        return copy_fixtures.build_hashtags(ctx)

    def build_reel_concept(self, ctx: CopyContext) -> ReelConcept:
        return copy_fixtures.build_reel_concept(ctx)

    def build_subheadline(self, ctx: CopyContext) -> str:
        return concept_fixtures.build_subheadline(ctx)
