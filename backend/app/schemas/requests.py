"""Request bodies. Mirror the input types in frontend/lib/api/types.ts."""

import uuid

from pydantic import BaseModel


class CreateCampaignIn(BaseModel):
    brand_id: uuid.UUID | None = None


class UpdateCampaignIn(BaseModel):
    # Every field is optional-and-nullable, and "absent" must stay
    # distinguishable from "explicitly null", exactly as the PATCH semantics in
    # the mock require. model_fields_set carries that distinction.
    objective: str | None = None
    audience: str | None = None
    visual_style: str | None = None
    brand_id: uuid.UUID | None = None


class ProductIn(BaseModel):
    name: str
    description: str | None = None
    price_text: str | None = None
    main_benefit: str | None = None
    brand_name: str | None = None


class AssetTextIn(BaseModel):
    headline_fa: str | None = None
    subheadline_fa: str | None = None
    cta_fa: str | None = None
    price_text: str | None = None


class BrandIn(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    instagram_handle: str | None = None
    website: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    visual_style: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None


class UpdateCopyIn(BaseModel):
    content: str


class RewriteIn(BaseModel):
    intent: str


class ResolveAssetsIn(BaseModel):
    paths: list[str]


class CropIn(BaseModel):
    x: float
    y: float
    width: float
    height: float
