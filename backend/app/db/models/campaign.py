import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ASSET_TYPES,
    CAMPAIGN_OBJECTIVES,
    CAMPAIGN_STATUSES,
    COPY_TYPES,
    JOB_STATUSES,
    JOB_TYPES,
    VISUAL_ATTEMPT_SOURCES,
    VISUAL_ATTEMPT_STATUSES,
    VISUAL_CANDIDATE_KINDS,
    VISUAL_CREATION_MODES,
    VISUAL_STYLES,
)
from app.db.base import (
    Base,
    created_timestamp,
    enum_check,
    json_column,
    pk,
    text_column,
    updated_timestamp,
    user_fk,
)


class Campaign(Base):
    """
    Spec §22 campaigns.

    Exactly one owner at a time: an anonymous session before signup, a user
    after adoption. The CHECK makes an orphaned campaign impossible.
    """

    __tablename__ = "campaigns"
    __table_args__ = (
        enum_check("campaigns", "objective", CAMPAIGN_OBJECTIVES, nullable=True),
        enum_check("campaigns", "visual_style", VISUAL_STYLES, nullable=True),
        enum_check(
            "campaigns",
            "visual_creation_mode",
            VISUAL_CREATION_MODES,
            nullable=True,
        ),
        enum_check("campaigns", "status", CAMPAIGN_STATUSES),
        CheckConstraint(
            "user_id is not null or anonymous_session_id is not null",
            name="ck_campaigns_has_owner",
        ),
        Index("ix_campaigns_user_created", "user_id", text("created_at desc")),
    )

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID | None] = user_fk()
    anonymous_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("anonymous_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    objective: Mapped[str | None] = text_column()
    audience: Mapped[str | None] = text_column()
    visual_style: Mapped[str | None] = text_column()
    visual_creation_mode: Mapped[str | None] = text_column()
    visual_recipe_json: Mapped[dict] = json_column("visual_recipe_json")
    planner_result_json: Mapped[dict] = json_column("planner_result_json")
    current_visual_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "campaign_visual_attempts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_campaigns_current_visual_attempt",
        ),
        nullable=True,
        index=True,
    )
    selected_concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'draft'")
    )
    is_free_campaign: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    # Which round of concepts the seller is on, so a regenerate returns
    # different Persian output. NULL until concepts are first requested, which
    # is how the mock's `concept_rounds[id] ?? -1` distinguished "never run"
    # from "round 0".
    concept_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class CampaignConcept(Base):
    """Spec §22 campaign_concepts."""

    __tablename__ = "campaign_concepts"

    id: Mapped[uuid.UUID] = pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_fa: Mapped[str] = mapped_column(String, nullable=False)
    headline_fa: Mapped[str] = mapped_column(String, nullable=False)
    description_fa: Mapped[str] = mapped_column(String, nullable=False)
    # Internal creative direction. Never rendered to the seller (spec §5.1, §23).
    visual_direction: Mapped[str] = mapped_column(String, nullable=False)
    background_prompt: Mapped[str] = mapped_column(String, nullable=False)
    raw_json: Mapped[dict] = json_column("raw_json")
    selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_timestamp()


class CampaignCopy(Base):
    """Spec §22 campaign_copy."""

    __tablename__ = "campaign_copy"
    __table_args__ = (enum_check("campaign_copy", "copy_type", COPY_TYPES),)

    id: Mapped[uuid.UUID] = pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    copy_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict] = json_column("metadata_json")
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class CampaignAsset(Base):
    """
    Spec §22 campaign_assets.

    `storage_path` stays null through Phase 2: the browser still composes each
    ad from `metadata_json` (an AssetRenderSpec). Phase 4/5 fill the path in and
    the renderer prefers it with no UI change.
    """

    __tablename__ = "campaign_assets"
    __table_args__ = (enum_check("campaign_assets", "asset_type", ASSET_TYPES),)

    id: Mapped[uuid.UUID] = pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str | None] = text_column()
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[str | None] = text_column()
    metadata_json: Mapped[dict] = json_column("metadata_json")
    created_at: Mapped[datetime] = created_timestamp()


class GenerationJob(Base):
    """
    Spec §22 generation_jobs.

    Every LLM call is recorded here so we can inspect provider, model, tokens
    and cost without building credits yet (spec §31 rule 10).
    """

    __tablename__ = "generation_jobs"
    __table_args__ = (
        enum_check("generation_jobs", "status", JOB_STATUSES),
        enum_check("generation_jobs", "job_type", JOB_TYPES),
        # Repeated taps on «ساخت کمپین» must not launch several jobs (spec §27).
        Index(
            "uq_generation_jobs_active",
            "campaign_id",
            "job_type",
            unique=True,
            postgresql_where=text(
                "status in ('queued', 'processing') "
                "AND job_type in ('campaign_generation', 'image_generation')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = user_fk()
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str | None] = text_column()
    model: Mapped[str | None] = text_column()
    provider_job_id: Mapped[str | None] = text_column()
    status: Mapped[str] = mapped_column(String, nullable=False)
    input_json: Mapped[dict] = json_column("input_json")
    output_json: Mapped[dict] = json_column("output_json")
    error_message: Mapped[str | None] = text_column()
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8), nullable=True
    )
    created_at: Mapped[datetime] = created_timestamp()
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CampaignVisualAttempt(Base):
    """One creative generation round: 3 candidates, optional repair, later Story."""

    __tablename__ = "campaign_visual_attempts"
    __table_args__ = (
        enum_check("campaign_visual_attempts", "source", VISUAL_ATTEMPT_SOURCES),
        enum_check(
            "campaign_visual_attempts", "status", VISUAL_ATTEMPT_STATUSES
        ),
        UniqueConstraint(
            "campaign_id",
            "attempt_number",
            name="uq_visual_attempts_campaign_number",
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    recipe_json: Mapped[dict] = json_column("recipe_json")
    planner_json: Mapped[dict] = json_column("planner_json")
    prompt_architect_json: Mapped[dict] = json_column("prompt_architect_json")
    status: Mapped[str] = mapped_column(String, nullable=False)
    auto_repair_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    selected_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "campaign_visual_candidates.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_visual_attempts_selected_candidate",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = created_timestamp()


class CampaignVisualCandidate(Base):
    """One 4:5 creative output. Previous attempts are never overwritten."""

    __tablename__ = "campaign_visual_candidates"
    __table_args__ = (
        enum_check(
            "campaign_visual_candidates", "kind", VISUAL_CANDIDATE_KINDS
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_visual_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'primary'")
    )
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    quality_json: Mapped[dict] = json_column("quality_json")
    hard_failed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    generation_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    variation_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = created_timestamp()

