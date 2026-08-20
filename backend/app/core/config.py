from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Backend configuration.

    Every provider, storage and auth concern is addressed through these values
    so that nothing in the service layer reaches for an environment variable
    directly (spec §23).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Database -------------------------------------------------------
    # Runtime connection. Least-privilege role: DML only, no DDL.
    database_url: str = (
        "postgresql+asyncpg://afarin_app:afarin_app@127.0.0.1:54322/postgres"
    )
    # Alembic only. Owns the tables.
    migration_database_url: str = (
        "postgresql+psycopg://afarin_migrator:afarin_migrator@127.0.0.1:54322/postgres"
    )
    # Bootstrap only, never used at runtime. Creates the two roles above.
    admin_database_url: str = (
        "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres"
    )

    afarin_migrator_password: str = "afarin_migrator"
    afarin_app_password: str = "afarin_app"

    db_echo: bool = False
    # Tests run each case in its own event loop, so a pooled asyncpg connection
    # cannot be reused across them. Production keeps the pool.
    db_null_pool: bool = False

    # --- Supabase -------------------------------------------------------
    supabase_url: str = "http://127.0.0.1:54321"
    # Storage operations only. Never leaves the backend.
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""
    # Fallback for local stacks still issuing HS256 tokens.
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    # --- Storage --------------------------------------------------------
    bucket_product_images: str = "product-images"
    bucket_brand_assets: str = "brand-assets"
    signed_url_ttl_seconds: int = 3600
    max_upload_bytes: int = 12 * 1024 * 1024
    max_product_images: int = 3

    # --- Anonymous session cookie ---------------------------------------
    anon_cookie_name: str = "afarin_anon"
    anon_cookie_secure: bool = False
    anon_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    anon_cookie_max_age: int = 60 * 60 * 24 * 30
    anon_cookie_domain: str | None = None
    anon_cookie_path: str = "/"

    # --- Behaviour ------------------------------------------------------
    content_provider: Literal["stub", "openrouter"] = "stub"
    image_provider: Literal["stub", "openrouter"] = "stub"
    openrouter_api_key: str = ""
    llm_model: str = "openai/gpt-5-mini"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_seconds: float = 45
    llm_max_retries: int = 2
    llm_http_referer: str = "http://localhost:3000"
    llm_app_title: str = "Afarin"
    # Empty = LLM_MODEL. Creative planner/quality vision stays env-configurable.
    visual_planner_model: str = ""
    # Until credits exist: initial creative generation + this many minus one
    # user-requested «سه نسخه جدید» rounds.
    max_creative_attempts_per_campaign: int = 3
    # Empty scenes only in accurate mode. Creative mode may send references.
    image_model: str = "bytedance-seed/seedream-4.5"
    # Seedream 4.5 rejects 1K for 4:5 / 9:16 (under ~3.7MP). 2K is valid.
    image_resolution: str = "2K"
    image_timeout_seconds: float = 120
    image_max_retries: int = 1
    # Phase 1 spent 900ms queued plus 13800ms of stages. Keeping the same total
    # means the progress screen behaves identically; tests set this to 0.
    generation_simulated_ms: int = 14700
    generation_queue_ms: int = 900
    # Dev-only hook mirroring the mock's ?failure= switch.
    allow_failure_injection: bool = False

    # Comma-separated. Kept as a string because a credentialed CORS response
    # must echo one exact origin, so this is an allowlist rather than a wildcard.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_allowed_origins.split(",")
        return [item.strip() for item in raw if item.strip()]

    @property
    def jwks_url(self) -> str:
        return self.supabase_jwks_url or (
            f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        )

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def planner_model(self) -> str:
        return self.visual_planner_model.strip() or self.llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
