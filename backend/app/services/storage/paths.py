"""
The `storage_path` contract.

Paths stay opaque to the frontend, which only ever hands them back to
`resolveAssetUrl`. Two schemes exist:

  public://mock/product-saffron.svg
      Ships with the frontend. Resolved synchronously in the browser so static
      imagery paints on first render.

  supabase://<bucket>/<key>
      Private object storage, resolved to a short-lived signed URL.

Object keys are anchored on the campaign, never the owner, which is what lets an
anonymous campaign be adopted by an account without moving a single byte.
"""

import uuid
from dataclasses import dataclass

PUBLIC_PREFIX = "public://"
SUPABASE_PREFIX = "supabase://"

SAMPLE_IMAGE_PATH = "public://mock/product-saffron.svg"


@dataclass(frozen=True, slots=True)
class StorageRef:
    bucket: str
    key: str

    def to_path(self) -> str:
        return f"{SUPABASE_PREFIX}{self.bucket}/{self.key}"


def is_public(path: str) -> bool:
    return path.startswith(PUBLIC_PREFIX)


def parse(path: str) -> StorageRef | None:
    """Returns None for anything that is not a private Supabase object."""
    if not path.startswith(SUPABASE_PREFIX):
        return None
    remainder = path[len(SUPABASE_PREFIX) :]
    bucket, separator, key = remainder.partition("/")
    if not separator or not bucket or not key:
        return None
    return StorageRef(bucket=bucket, key=key)


@dataclass(frozen=True, slots=True)
class OwnerScope:
    """Which record's ownership governs an object, derived from its key."""

    kind: str  # "campaign" | "brand"
    id: uuid.UUID


def owner_scope(ref: StorageRef) -> OwnerScope | None:
    """
    Recovers the owning record from an object key so a signed URL can be refused
    for someone else's asset. Unparseable keys return None and are denied.
    """
    parts = ref.key.split("/")
    try:
        if len(parts) >= 2 and parts[0] == "campaigns":
            return OwnerScope("campaign", uuid.UUID(parts[1]))
        if len(parts) >= 2 and parts[0] == "brands":
            return OwnerScope("brand", uuid.UUID(parts[1]))
    except ValueError:
        return None
    return None


def product_image_key(campaign_id: uuid.UUID, image_id: uuid.UUID, ext: str) -> str:
    return f"campaigns/{campaign_id}/products/{image_id}.{ext}"


def brand_asset_key(brand_id: uuid.UUID, asset_id: uuid.UUID, ext: str) -> str:
    return f"brands/{brand_id}/{asset_id}.{ext}"
