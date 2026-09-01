from app.db.base import Base
from app.db.models.brand import Brand, BrandAsset
from app.db.models.campaign import (
    Campaign,
    CampaignAsset,
    CampaignConcept,
    CampaignCopy,
    CampaignVisualAttempt,
    CampaignVisualCandidate,
    GenerationJob,
)
from app.db.models.chat import ChatArtifact, ChatConversation, ChatMessage
from app.db.models.education import EducationalPost, EducationalTheme
from app.db.models.identity import AnonymousSession, Profile
from app.db.models.product import Product, ProductImage

__all__ = [
    "APP_TABLES",
    "BROWSER_ROLES",
    "OWNER_ROLE",
    "RUNTIME_ROLE",
    "AnonymousSession",
    "Base",
    "Brand",
    "BrandAsset",
    "Campaign",
    "CampaignAsset",
    "CampaignConcept",
    "CampaignCopy",
    "CampaignVisualAttempt",
    "CampaignVisualCandidate",
    "ChatArtifact",
    "ChatConversation",
    "ChatMessage",
    "EducationalPost",
    "EducationalTheme",
    "GenerationJob",
    "Product",
    "ProductImage",
    "Profile",
]

#: The role the API connects as. Every app table carries one RLS policy naming
#: it, so the backend works without BYPASSRLS (see the Phase 2 RLS migration).
RUNTIME_ROLE = "afarin_app"

#: The role that owns the tables and runs migrations.
OWNER_ROLE = "afarin_migrator"

#: PostgREST's browser-facing roles. Nothing here is theirs.
BROWSER_ROLES: tuple[str, ...] = ("anon", "authenticated")

APP_TABLES: tuple[str, ...] = (
    "profiles",
    "anonymous_sessions",
    "brands",
    "brand_assets",
    "products",
    "product_images",
    "campaigns",
    "campaign_concepts",
    "campaign_copy",
    "campaign_assets",
    "generation_jobs",
    "campaign_visual_attempts",
    "campaign_visual_candidates",
    "educational_themes",
    "educational_posts",
    "chat_conversations",
    "chat_messages",
    "chat_artifacts",
)
