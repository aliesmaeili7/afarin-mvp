"""
Upload rules, re-checked server side.

The browser already downscales and validates before sending, but the client is
not a trust boundary, so every rule is enforced again here.
"""

import io

from httpx import AsyncClient
from PIL import Image

from tests.conftest import png_bytes


async def _campaign(client: AsyncClient) -> str:
    return (await client.post("/api/campaigns", json={})).json()["id"]


def _jpeg(width: int = 32) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, width), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


async def test_upload_is_stored_privately_and_marked_primary(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _campaign(client)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("a.png", png_bytes(), "image/png"))],
    )
    assert response.status_code == 200

    image = response.json()[0]
    assert image["is_primary"] is True
    assert image["storage_path"].endswith(".png")
    assert len(storage.objects) == 1


async def test_fourth_image_is_refused(client: AsyncClient, storage) -> None:
    campaign_id = await _campaign(client)

    for _ in range(3):
        ok = await client.post(
            f"/api/campaigns/{campaign_id}/images",
            files=[("files", ("a.png", png_bytes(), "image/png"))],
        )
        assert ok.status_code == 200

    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("d.png", png_bytes(), "image/png"))],
    )
    assert response.status_code == 422
    assert response.json()["message_fa"] == "حداکثر ۳ عکس می‌تونی اضافه کنی."


async def test_pdf_masquerading_as_png_is_refused(client: AsyncClient, storage) -> None:
    campaign_id = await _campaign(client)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("fake.png", b"%PDF-1.4 not an image", "image/png"))],
    )
    assert response.status_code == 422
    assert response.json()["message_fa"] == "این فایل یک عکس معتبر نیست."
    assert storage.objects == {}


async def test_unsupported_type_is_refused(client: AsyncClient, storage) -> None:
    campaign_id = await _campaign(client)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("a.gif", png_bytes(), "image/gif"))],
    )
    assert response.status_code == 422
    assert (
        response.json()["message_fa"] == "فقط عکس با فرمت JPG، PNG یا WEBP قابل قبوله."
    )


async def test_oversized_upload_is_refused(client: AsyncClient, storage) -> None:
    campaign_id = await _campaign(client)
    huge = png_bytes(2400, 2400) + b"\0" * (13 * 1024 * 1024)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("big.png", huge, "image/png"))],
    )
    assert response.status_code == 422
    assert (
        response.json()["message_fa"]
        == "حجم عکس بیشتر از ۱۲ مگابایته. یه عکس سبک‌تر انتخاب کن."
    )


async def test_deleting_the_primary_promotes_the_next_image(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _campaign(client)

    first = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("a.png", png_bytes(), "image/png"))],
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("b.jpg", _jpeg(), "image/jpeg"))],
    )

    deleted = await client.delete(
        f"/api/campaigns/{campaign_id}/images/{first.json()[0]['id']}"
    )
    assert deleted.status_code == 204
    # The object is removed from storage too, not just the row.
    assert len(storage.objects) == 1

    detail = await client.get(f"/api/campaigns/{campaign_id}")
    images = detail.json()["product_images"]
    assert len(images) == 1
    assert images[0]["is_primary"] is True


async def test_sample_product_uses_a_bundled_asset(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _campaign(client)

    response = await client.post(f"/api/campaigns/{campaign_id}/images/sample")
    assert response.status_code == 200
    assert response.json()[0]["storage_path"] == "public://mock/product-saffron.svg"

    detail = await client.get(f"/api/campaigns/{campaign_id}")
    assert detail.json()["product"]["name"] == "زعفران ممتاز"


async def test_product_name_is_required(client: AsyncClient) -> None:
    campaign_id = await _campaign(client)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/product", json={"name": "   "}
    )
    assert response.status_code == 422
    assert response.json()["message_fa"] == "اسم محصول رو بنویس."
