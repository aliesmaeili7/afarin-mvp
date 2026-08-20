"""
Wire shapes.

Field names and nullability mirror frontend/types/domain.ts exactly, so the
frontend consumes FastAPI responses without reshaping anything.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _iso_z(value: datetime) -> str:
    """
    Matches JavaScript's toISOString(), which the Phase 1 mock produced and the
    dashboard sorts on with a plain string comparison.
    """
    moment = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


Timestamp = Annotated[datetime, PlainSerializer(_iso_z, return_type=str)]
Id = Annotated[uuid.UUID, PlainSerializer(str, return_type=str)]
OptionalId = Annotated[
    uuid.UUID | None,
    PlainSerializer(lambda v: str(v) if v else None, return_type=str | None),
]


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BrandOut(Model):
    id: Id
    user_id: OptionalId
    name: str
    description: str | None
    category: str | None
    instagram_handle: str | None
    website: str | None
    target_audience: str | None
    tone: str | None
    visual_style: str | None
    primary_color: str | None
    secondary_color: str | None
    created_at: Timestamp
    updated_at: Timestamp


class ProductOut(Model):
    id: Id
    user_id: OptionalId
    brand_id: OptionalId
    name: str
    description: str | None
    price_text: str | None
    main_benefit: str | None
    created_at: Timestamp
    updated_at: Timestamp


class ProductImageOut(Model):
    id: Id
    product_id: Id
    storage_path: str
    is_primary: bool
    crop: dict[str, float]
    crop_storage_path: str | None
    created_at: Timestamp


class CampaignOut(Model):
    id: Id
    user_id: OptionalId
    anonymous_session_id: OptionalId
    brand_id: OptionalId
    product_id: OptionalId
    objective: str | None
    audience: str | None
    visual_style: str | None
    selected_concept_id: OptionalId
    status: str
    is_free_campaign: bool
    created_at: Timestamp
    updated_at: Timestamp


class CampaignConceptOut(Model):
    id: Id
    campaign_id: Id
    concept_number: int
    title_fa: str
    headline_fa: str
    description_fa: str
    visual_direction: str
    background_prompt: str
    raw_json: dict[str, Any]
    selected: bool
    created_at: Timestamp


class CampaignCopyOut(Model):
    id: Id
    campaign_id: Id
    copy_type: str
    content: str
    metadata_json: dict[str, Any]
    created_at: Timestamp
    updated_at: Timestamp


class CampaignAssetOut(Model):
    id: Id
    campaign_id: Id
    asset_type: str
    storage_path: str | None
    width: int
    height: int
    template_id: str | None
    metadata_json: dict[str, Any]
    created_at: Timestamp


class CampaignDetailOut(Model):
    campaign: CampaignOut
    product: ProductOut | None
    product_images: list[ProductImageOut]
    concepts: list[CampaignConceptOut]
    copies: list[CampaignCopyOut]
    assets: list[CampaignAssetOut]
    brand: BrandOut | None


class CampaignSummaryOut(Model):
    id: Id
    product_name: str | None
    brand_name: str | None
    status: str
    # The rendered feed ad once one exists, otherwise the source photo.
    thumbnail_path: str | None
    # Lets the dashboard show the finished ad rather than the raw upload while
    # assets are still composed in the browser. Null until a campaign is ready.
    thumbnail_spec: dict[str, Any] | None
    created_at: Timestamp


class CampaignStatusOut(Model):
    campaign_id: Id
    status: str
    stage: str | None
    percent: int
    message_fa: str | None
    failed_asset_types: list[str]


class SessionUserOut(Model):
    id: Id
    email: str
    display_name: str
    locale: str
    free_campaigns_remaining: int


class SessionOut(Model):
    user: SessionUserOut
    access_token: str
