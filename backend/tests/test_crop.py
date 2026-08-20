"""Subject crop for messy Instagram-style uploads."""

import io
import uuid

from httpx import AsyncClient
from PIL import Image

from app.services.campaigns.crop import apply_crop, parse_crop, suggest_crop
from app.services.campaigns.cutout import NullCutout, set_cutout
from tests.conftest import auth_header, png_bytes
from tests.test_visuals import _generate, _ready_campaign


def instagram_screenshot(*, kind: str = "cosmetics") -> bytes:
    """
    Letterboxed screenshot: Instagram chrome, black bars, product in the middle.
    """
    width, height = 400, 800
    image = Image.new("RGB", (width, height), (8, 8, 8))
    pixels = image.load()
    assert pixels is not None
    for y in range(0, 90):
        for x in range(width):
            pixels[x, y] = (12, 12, 12)
    for y in range(90, 130):
        for x in range(width):
            pixels[x, y] = (18, 18, 22)
    for y in range(height - 110, height):
        for x in range(width):
            pixels[x, y] = (6, 6, 6)
    fill = {
        "cosmetics": (220, 80, 140),
        "sweatshirt": (40, 90, 160),
        "food": (200, 90, 40),
    }[kind]
    for y in range(180, 620):
        for x in range(90, 310):
            pixels[x, y] = fill
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def test_suggest_crop_trims_letterbox_and_chrome() -> None:
    for kind in ("cosmetics", "sweatshirt", "food"):
        rect = suggest_crop(instagram_screenshot(kind=kind))
        assert 0.15 < rect.y < 0.35
        assert rect.y + rect.height < 0.92
        assert rect.height > 0.4
        cropped = Image.open(
            io.BytesIO(apply_crop(instagram_screenshot(kind=kind), rect))
        )
        assert cropped.size[1] < 700
        assert cropped.size[0] <= 400


def test_parse_crop_rejects_tiny_boxes() -> None:
    try:
        parse_crop({"x": 0.4, "y": 0.4, "width": 0.05, "height": 0.05})
    except ValueError:
        return
    raise AssertionError("tiny crop should be rejected")


async def test_upload_persists_crop_and_leaves_original(
    client: AsyncClient, storage
) -> None:
    campaign_id = (await client.post("/api/campaigns", json={})).json()["id"]
    raw = instagram_screenshot()
    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("ig.jpg", raw, "image/jpeg"))],
    )
    assert response.status_code == 200
    image = response.json()[0]
    original_path = image["storage_path"]
    crop_path = image["crop_storage_path"]
    assert crop_path
    assert original_path != crop_path
    assert "/crops/" in crop_path
    assert image["crop"]["height"] < 0.95

    from app.services.storage.paths import parse

    original_ref = parse(original_path)
    crop_ref = parse(crop_path)
    assert original_ref is not None and crop_ref is not None
    stored_original = storage.objects[f"{original_ref.bucket}/{original_ref.key}"]
    stored_crop = storage.objects[f"{crop_ref.bucket}/{crop_ref.key}"]
    assert stored_original == raw
    assert stored_crop != raw
    crop_image = Image.open(io.BytesIO(stored_crop))
    full_image = Image.open(io.BytesIO(stored_original))
    assert crop_image.size[1] < full_image.size[1]

    tighter = await client.patch(
        f"/api/campaigns/{campaign_id}/images/{image['id']}/crop",
        json={"x": 0.2, "y": 0.25, "width": 0.55, "height": 0.5},
    )
    assert tighter.status_code == 200
    assert tighter.json()["crop"] == {
        "x": 0.2,
        "y": 0.25,
        "width": 0.55,
        "height": 0.5,
    }
    assert storage.objects[f"{original_ref.bucket}/{original_ref.key}"] == raw

    detail = await client.get(f"/api/campaigns/{campaign_id}")
    saved = detail.json()["product_images"][0]
    assert saved["crop"]["height"] == 0.5
    assert saved["crop_storage_path"] == tighter.json()["crop_storage_path"]
    assert "/crops/" in saved["crop_storage_path"]


async def test_invalid_crop_is_rejected(client: AsyncClient, storage) -> None:
    campaign_id = (await client.post("/api/campaigns", json={})).json()["id"]
    uploaded = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("a.png", png_bytes(), "image/png"))],
    )
    image_id = uploaded.json()[0]["id"]
    response = await client.patch(
        f"/api/campaigns/{campaign_id}/images/{image_id}/crop",
        json={"x": 0.0, "y": 0.0, "width": 0.05, "height": 0.05},
    )
    assert response.status_code == 422
    assert response.json()["message_fa"] == "کادر محصول رو یک مقدار بزرگ‌تر انتخاب کن."


async def test_cutout_uses_crop_not_full_screenshot(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    raw = instagram_screenshot(kind="sweatshirt")
    uploaded = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        headers=headers,
        files=[("files", ("ig.jpg", raw, "image/jpeg"))],
    )
    original = uploaded.json()[0]["storage_path"]
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "هودی"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    concepts = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/generate", headers=headers
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concepts.json()[1]['id']}/select",
        headers=headers,
    )
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "ready"
    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    feed = next(
        row for row in detail.json()["assets"] if row["asset_type"] == "feed_final"
    )
    product_path = feed["metadata_json"]["product_image_path"]
    assert product_path != original
    assert "cutouts/" in product_path
    assert "/products/" not in product_path
    assert feed["metadata_json"]["product_source"] == "cutout"


async def test_missing_rembg_uses_crop_not_screenshot(
    client: AsyncClient, storage
) -> None:
    set_cutout(NullCutout())
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready_campaign(client, headers)
    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    image = detail.json()["product_images"][0]
    status = await _generate(client, headers, campaign_id)
    assert status.json()["status"] == "ready"
    after = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    feed = next(
        row for row in after.json()["assets"] if row["asset_type"] == "feed_final"
    )
    product_path = feed["metadata_json"]["product_image_path"]
    assert product_path != image["storage_path"]
    assert "/crops/" in product_path
    assert feed["metadata_json"]["product_source"] == "crop"
    assert "cutouts/" not in product_path
