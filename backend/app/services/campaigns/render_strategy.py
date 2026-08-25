"""Internal creative render-strategy selector.

Default is reference_transform. preserved_product_composite is a narrow
allow-list: isolatable packaged objects on simple display templates, with a
validated cutout and a placement that can plausibly sit on the generated
contact surface. Uncertain or worn/used/surreal cases stay transform.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.content.visual_catalog import template_by_id
from app.providers.vision.base import ArchitectCandidate, ProductPlacement

REFERENCE_TRANSFORM = "reference_transform"
PRESERVED_PRODUCT_COMPOSITE = "preserved_product_composite"

PRESERVED_TEMPLATES = frozenset(
    {
        "hero_product",
        "product_pedestal",
        "collage",
        "product_with_props",
        "floating_product",
        "flat_lay",
    }
)
FORCE_TRANSFORM_TEMPLATES = frozenset(
    {
        "giant_miniature_world",
        "surreal_scale",
        "cinematic_environment",
        "illustrated_scene",
        "model_using",
        "character_poster",
    }
)
APPAREL_MARKERS = (
    "clothing",
    "apparel",
    "fashion",
    "hoodie",
    "sweatshirt",
    "garment",
    "shirt",
    "dress",
    "jacket",
)
FOOD_MARKERS = ("food", "plated", "dish", "restaurant", "meal", "plate")
OBJECT_MARKERS = (
    "cosmetics",
    "beauty",
    "packaging",
    "package",
    "jar",
    "bottle",
    "shoes",
    "footwear",
    "sneaker",
    "accessory",
    "object",
    "candle",
    "soap",
)
HARD_SURFACES = frozenset(
    {
        "table",
        "plinth",
        "pedestal",
        "shelf",
        "floor",
        "counter",
        "surface",
        "marble",
        "wood",
        "stone",
        "linen",
        "stand",
    }
)
FLOATING_SURFACES = frozenset({"none", "air", "void", "shadow_only", "floating"})
WORN_POSE_MARKERS = (
    "worn",
    "wearing",
    "held",
    "holding",
    "hand",
    "hands",
    "person",
    "model",
    "pose",
)
EXTREME_CAMERA_MARKERS = (
    "dutch",
    "worm's eye",
    "worms eye",
    "extreme",
    "tilted",
    "overhead",
    "bird's eye",
    "birds eye",
    "top-down",
    "top down",
)

MAX_ROTATION_DEGREES = 8.0
MIN_PLACEMENT_WIDTH = 0.28
MAX_PLACEMENT_WIDTH = 0.65
MIN_MARGIN = 0.04


@dataclass(frozen=True, slots=True)
class RenderStrategyChoice:
    strategy: str
    reason: str


def choose_creative_render_strategy(
    *,
    style_id: str,
    template_id: str,
    analysis: dict | None = None,
    product_type: str | None = None,
    category: str | None = None,
    cutout_png: bytes | None = None,
) -> RenderStrategyChoice:
    del style_id
    payload = analysis or {}
    kind = _kind_text(product_type, category, payload.get("product_type"))
    if template_id in FORCE_TRANSFORM_TEMPLATES:
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, f"template {template_id} requires a generated product"
        )
    if _template_needs_person(template_id):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM,
            "template requires a person wearing or using the product",
        )
    if _matches(kind, FOOD_MARKERS):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, "plated food cannot be pasted as a cutout"
        )
    if _matches(kind, APPAREL_MARKERS):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, "apparel identity is safer as a reference transform"
        )
    if payload.get("person_present"):
        return RenderStrategyChoice(REFERENCE_TRANSFORM, "reference includes a person")
    if payload.get("useful_context_present"):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, "reference includes useful worn/used context"
        )
    if cutout_png is None:
        return RenderStrategyChoice(REFERENCE_TRANSFORM, "no validated cutout")
    if template_id not in PRESERVED_TEMPLATES:
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM,
            f"template {template_id} is outside the preserved allow-list",
        )
    if not _isolatable(payload):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, "product is not an isolatable still-life object"
        )
    if kind and not _matches(kind, OBJECT_MARKERS):
        return RenderStrategyChoice(
            REFERENCE_TRANSFORM, "product type is not a packaged/object still"
        )
    return RenderStrategyChoice(
        PRESERVED_PRODUCT_COMPOSITE,
        "isolatable object on a simple display template with a validated cutout",
    )


def placement_can_integrate(
    candidate: ArchitectCandidate,
    *,
    template_id: str,
) -> tuple[bool, str]:
    if not candidate.has_product_placement or candidate.product_placement is None:
        return False, "architect did not supply a usable product placement"
    placement = candidate.product_placement
    pose = (candidate.composition.human_or_pose or "").lower()
    if any(marker in pose for marker in WORN_POSE_MARKERS):
        return False, "placement implies a person holding or wearing the product"
    position = (candidate.composition.product_position or "").lower()
    if any(marker in position for marker in WORN_POSE_MARKERS):
        return False, "product position is worn or held"
    camera = (candidate.composition.camera or "").lower()
    if template_id != "flat_lay" and any(
        marker in camera for marker in EXTREME_CAMERA_MARKERS
    ):
        return False, "camera perspective cannot take a pasted product"
    if abs(placement.rotation_degrees) > MAX_ROTATION_DEGREES:
        return False, "rotation is too large for a conservative paste"
    if placement.width < MIN_PLACEMENT_WIDTH or placement.width > MAX_PLACEMENT_WIDTH:
        return False, "placement scale is not a plausible product still"
    surface = _norm_surface(placement.contact_surface)
    if template_id == "floating_product":
        if (
            surface
            and surface not in FLOATING_SURFACES
            and surface not in HARD_SURFACES
        ):
            return False, "floating contact surface is not plausible"
    elif surface not in HARD_SURFACES:
        return False, "contact surface cannot plausibly hold the real product"
    height = placement.width * 1.25
    left = placement.x - placement.width / 2
    right = placement.x + placement.width / 2
    top = placement.y - height / 2
    bottom = placement.y + height / 2
    if left < MIN_MARGIN or top < MIN_MARGIN or right > 1 - MIN_MARGIN or bottom > 1.05:
        return False, "placement would clip or overflow the frame"
    return True, "placement can sit on the designed contact surface"


def _template_needs_person(template_id: str) -> bool:
    try:
        item = template_by_id(template_id)
    except KeyError:
        return template_id in {"model_using", "character_poster"}
    return item.get("human_requirement") == "required" or bool(item.get("needs_person"))


def _isolatable(payload: dict) -> bool:
    cleanliness = str(payload.get("cleanliness") or "")
    return cleanliness in {"isolatable_subject", "clean"} and not payload.get(
        "person_present"
    )


def _kind_text(*parts: str | None) -> str:
    return " ".join(str(part or "").lower() for part in parts).strip()


def _matches(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _norm_surface(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def empty_placement() -> ProductPlacement:
    return ProductPlacement()
