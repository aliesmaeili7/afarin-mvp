from typing import Protocol

from app.content.concepts import ConceptDraft
from app.content.context import CopyContext
from app.content.copy import CaptionSet, ReelConcept


class ContentProvider(Protocol):
    """
    Everything that writes Persian campaign text.

    Phase 2 ships only StubContentProvider. Phase 3 adds an LLM-backed
    implementation and selects it through `CONTENT_PROVIDER`; nothing in the
    service layer calls a provider SDK directly (spec §23).
    """

    def build_concepts(self, ctx: CopyContext) -> list[ConceptDraft]: ...

    def build_captions(self, ctx: CopyContext) -> CaptionSet: ...

    def build_story_ideas(self, ctx: CopyContext) -> list[str]: ...

    def build_primary_cta(self, ctx: CopyContext) -> str: ...

    def build_hashtags(self, ctx: CopyContext) -> str: ...

    def build_reel_concept(self, ctx: CopyContext) -> ReelConcept: ...

    def build_subheadline(self, ctx: CopyContext) -> str: ...
