import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import EDUCATION_THEME_SOURCES, EDUCATIONAL_POST_STATUSES
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


class EducationalTheme(Base):
    """
    A reusable visual system, saved so a teacher's posts look like one series.

    Holds palette, illustration style, mood, lighting, shape language and motifs.
    Never the topic, headline, overlay copy or prompt of the post it came from: the point is
    that a later post about a different subject still looks like the same
    account. `services/education/themes.py` enforces that on save.
    """

    __tablename__ = "educational_themes"
    __table_args__ = (
        enum_check("educational_themes", "source", EDUCATION_THEME_SOURCES),
        Index(
            "ix_educational_themes_user_created",
            "user_id",
            text("created_at desc"),
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    theme_json: Mapped[dict] = json_column("theme_json")
    source: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'user'")
    )
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()


class EducationalPost(Base):
    """
    One educational Instagram post: a prompt in, a square image plus overlay
    text out.

    Unlike `campaigns` this has a single owner and no anonymous variant. A
    visitor may type a prompt and pick a theme, but that stays in the browser
    until they sign in; the row is only created once generation is authorized.
    So `user_id` is NOT NULL and there is no owner CHECK to write.

    Caption and hashtags are read back out of `agent_json` rather than copied
    into columns, keeping one source of truth for the agent's output.
    """

    __tablename__ = "educational_posts"
    __table_args__ = (
        enum_check("educational_posts", "status", EDUCATIONAL_POST_STATUSES),
        Index(
            "ix_educational_posts_user_created",
            "user_id",
            text("created_at desc"),
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    user_prompt: Mapped[str] = mapped_column(String, nullable=False)
    selected_theme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("educational_themes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    #: A builtin theme id when the user picked one from app/content. Kept
    #: separate from selected_theme_id because builtins are not table rows.
    selected_builtin_theme_id: Mapped[str | None] = text_column()
    language: Mapped[str | None] = text_column()
    #: Denormalized so the dashboard can list posts without parsing agent_json.
    headline: Mapped[str | None] = text_column()
    agent_json: Mapped[dict] = json_column("agent_json")
    #: The effective theme: the selected one's snapshot, or the agent's design.
    theme_json: Mapped[dict] = json_column("theme_json")
    #: The editable AssetRenderSpec the browser renders and exports.
    render_spec_json: Mapped[dict] = json_column("render_spec_json")
    image_storage_path: Mapped[str | None] = text_column()
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'queued'")
    )
    error_message: Mapped[str | None] = text_column()
    #: One perf_counter delta across the whole run. Never a sum of provider
    #: latencies, so it stays comparable with advertising wall time.
    wall_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = created_timestamp()
    updated_at: Mapped[datetime] = updated_timestamp()
