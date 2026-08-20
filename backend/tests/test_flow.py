"""
The journey the spec is actually about: a stranger uploads a photo, gets a
campaign, signs up, and finds it waiting for them.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, png_bytes


async def _draft_campaign(client: AsyncClient) -> str:
    response = await client.post("/api/campaigns", json={})
    assert response.status_code == 200
    return response.json()["id"]


async def _complete_brief(client: AsyncClient, campaign_id: str) -> None:
    product = await client.post(
        f"/api/campaigns/{campaign_id}/product",
        json={
            "name": "زعفران ممتاز",
            "price_text": "۳۹۹ هزار تومان",
            "main_benefit": "بسته‌بندی هدیه",
            "brand_name": "سحند",
        },
    )
    assert product.status_code == 200

    patch = await client.patch(
        f"/api/campaigns/{campaign_id}",
        json={
            "objective": "sell_product",
            "visual_style": "luxury",
            "audience": "هدیه",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "brief_complete"


async def _select_first_concept(client: AsyncClient, campaign_id: str) -> None:
    concepts = await client.post(f"/api/campaigns/{campaign_id}/concepts/generate")
    assert concepts.status_code == 200
    assert len(concepts.json()) == 3

    concept_id = concepts.json()[0]["id"]
    selected = await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{concept_id}/select"
    )
    assert selected.status_code == 200
    assert selected.json()["selected_concept_id"] == concept_id


async def test_anonymous_visitor_gets_a_cookie_not_a_readable_token(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/campaigns", json={})
    assert response.status_code == 200

    cookie = response.cookies.get("afarin_anon")
    assert cookie, "the backend must mint an anonymous session"

    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    # The token must never be readable by page scripts.
    assert cookie not in response.text


async def test_anonymous_campaign_is_invisible_to_another_visitor(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _draft_campaign(client)

    stranger = AsyncClient(transport=client._transport, base_url="http://api.test")
    async with stranger:
        response = await stranger.get(f"/api/campaigns/{campaign_id}")

    assert response.status_code == 403
    assert response.json() == {
        "code": "unauthorized",
        "message_fa": "دسترسی به این کمپین برای شما مجاز نیست.",
    }


async def test_unknown_campaign_reads_as_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/api/campaigns/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["message_fa"] == "این کمپین پیدا نشد."


async def test_generation_requires_signing_in(client: AsyncClient, storage) -> None:
    campaign_id = await _draft_campaign(client)
    await _complete_brief(client, campaign_id)
    await _select_first_concept(client, campaign_id)

    response = await client.post(f"/api/campaigns/{campaign_id}/generate")
    assert response.status_code == 403
    assert response.json()["message_fa"] == "برای ساخت کمپین اول باید وارد بشی."


async def test_signed_in_user_can_generate_a_second_campaign(
    client: AsyncClient, storage
) -> None:
    first_id = await _draft_campaign(client)
    await _complete_brief(client, first_id)
    await _select_first_concept(client, first_id)

    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    await client.post(f"/api/campaigns/{first_id}/generate", headers=headers)
    await client.get(f"/api/campaigns/{first_id}/status", headers=headers)

    second_id = (await client.post("/api/campaigns", json={}, headers=headers)).json()[
        "id"
    ]
    await client.post(
        f"/api/campaigns/{second_id}/product",
        headers=headers,
        json={"name": "صابون زیتون", "brand_name": "زیتونک"},
    )
    await client.patch(
        f"/api/campaigns/{second_id}",
        headers=headers,
        json={"objective": "sell_product", "visual_style": "minimal"},
    )
    concepts = await client.post(
        f"/api/campaigns/{second_id}/concepts/generate", headers=headers
    )
    assert concepts.status_code == 200
    first_detail = await client.get(f"/api/campaigns/{first_id}", headers=headers)
    first_ids = {row["id"] for row in first_detail.json()["concepts"]}
    second_ids = {row["id"] for row in concepts.json()}
    assert second_ids.isdisjoint(first_ids)

    await client.post(
        f"/api/campaigns/{second_id}/concepts/{concepts.json()[0]['id']}/select",
        headers=headers,
    )
    started = await client.post(f"/api/campaigns/{second_id}/generate", headers=headers)
    assert started.status_code == 200


async def test_changing_brief_invalidates_concepts(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _draft_campaign(client)
    await _complete_brief(client, campaign_id)
    generated = await client.post(f"/api/campaigns/{campaign_id}/concepts/generate")
    assert len(generated.json()) == 3
    await client.post(
        f"/api/campaigns/{campaign_id}/concepts/{generated.json()[0]['id']}/select"
    )

    patched = await client.patch(
        f"/api/campaigns/{campaign_id}", json={"visual_style": "minimal"}
    )
    assert patched.json()["status"] == "brief_complete"
    assert patched.json()["selected_concept_id"] is None

    detail = await client.get(f"/api/campaigns/{campaign_id}")
    assert detail.json()["concepts"] == []

    regenerated = await client.post(f"/api/campaigns/{campaign_id}/concepts/generate")
    assert len(regenerated.json()) == 3
    kept = await client.patch(
        f"/api/campaigns/{campaign_id}", json={"visual_style": "minimal"}
    )
    assert kept.json()["status"] == "concepts_ready"
    same = await client.get(f"/api/campaigns/{campaign_id}")
    assert len(same.json()["concepts"]) == 3

    renamed = await client.post(
        f"/api/campaigns/{campaign_id}/product",
        json={"name": "صابون زیتون", "brand_name": "سحند"},
    )
    assert renamed.status_code == 200
    after_rename = await client.get(f"/api/campaigns/{campaign_id}")
    assert after_rename.json()["concepts"] == []
    assert after_rename.json()["campaign"]["status"] == "brief_complete"


async def test_full_anonymous_to_dashboard_journey(
    client: AsyncClient, storage
) -> None:
    campaign_id = await _draft_campaign(client)

    upload = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("product.png", png_bytes(), "image/png"))],
    )
    assert upload.status_code == 200
    stored_path = upload.json()[0]["storage_path"]
    assert stored_path.startswith("supabase://product-images/campaigns/")
    # Keyed by campaign, so adoption never has to move an object.
    assert campaign_id in stored_path

    await _complete_brief(client, campaign_id)
    await _select_first_concept(client, campaign_id)

    user_id = uuid.uuid4()
    headers = auth_header(user_id)

    adopt = await client.post("/api/session/adopt", headers=headers)
    assert adopt.status_code == 200
    assert adopt.json()["user"]["email"] == "seller@example.com"

    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["campaign"]["user_id"] == str(user_id)
    assert detail.json()["campaign"]["anonymous_session_id"] is None

    started = await client.post(
        f"/api/campaigns/{campaign_id}/generate", headers=headers
    )
    assert started.status_code == 200

    status = await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert status.json()["percent"] == 100

    final = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    payload = final.json()
    assert {asset["asset_type"] for asset in payload["assets"]} >= {
        "feed_final",
        "story_final",
        "carousel_1",
        "carousel_2",
        "carousel_3",
        "generated_background",
        "product_cutout",
    }
    feed = next(
        asset for asset in payload["assets"] if asset["asset_type"] == "feed_final"
    )
    assert feed["storage_path"] is None
    assert feed["metadata_json"]["scene_image_path"]
    assert feed["metadata_json"]["product_image_path"] != stored_path
    copy_types = {copy["copy_type"] for copy in payload["copies"]}
    assert {"caption_short", "caption_friendly", "caption_persuasive"} <= copy_types
    assert "story" in copy_types and "hashtags" in copy_types

    dashboard = await client.get("/api/campaigns", headers=headers)
    cards = dashboard.json()
    generated = next(card for card in cards if card["id"] == campaign_id)
    # The dashboard shows the finished ad, not the raw upload.
    assert generated["thumbnail_spec"] is not None
    assert generated["thumbnail_spec"]["headline_fa"]
    assert generated["product_name"] == "زعفران ممتاز"
    assert generated["brand_name"] == "سحند"

    # Signing up also seeded a sample campaign, so the dashboard is never empty.
    assert len(cards) == 2
    sample = next(card for card in cards if card["id"] != campaign_id)
    assert sample["thumbnail_path"] == "public://mock/product-saffron.svg"


async def test_adoption_is_single_use(client: AsyncClient, storage) -> None:
    campaign_id = await _draft_campaign(client)

    first = uuid.uuid4()
    adopted = await client.post("/api/session/adopt", headers=auth_header(first))
    assert adopted.status_code == 200

    # The cookie is cleared on success, so the second account inherits nothing.
    second = uuid.uuid4()
    await client.post("/api/session/adopt", headers=auth_header(second, "other@x.com"))

    response = await client.get(
        f"/api/campaigns/{campaign_id}", headers=auth_header(second, "other@x.com")
    )
    assert response.status_code == 403


async def test_brand_kit_persists_across_devices(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    headers = auth_header(user_id)
    await client.post("/api/session/adopt", headers=headers)

    created = await client.post(
        "/api/brands",
        headers=headers,
        json={"name": "سحند", "tone": "لوکس", "visual_style": "luxury"},
    )
    assert created.status_code == 200

    # A different browser: no cookies at all, only the account's token.
    other_device = AsyncClient(transport=client._transport, base_url="http://api.test")
    async with other_device:
        listed = await other_device.get("/api/brands", headers=headers)

    names = [brand["name"] for brand in listed.json()]
    assert "سحند" in names


async def test_brand_name_is_required(client: AsyncClient) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)

    response = await client.post("/api/brands", headers=headers, json={"name": "  "})
    assert response.status_code == 422
    assert response.json()["message_fa"] == "اسم برند رو بنویس."


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {"objective": "sell_product"},
            "برای ساخت ایده، هدف و سبک تبلیغ رو انتخاب کن.",
        ),
        ({"visual_style": "luxury"}, "برای ساخت ایده، هدف و سبک تبلیغ رو انتخاب کن."),
    ],
)
async def test_incomplete_brief_blocks_concepts(
    client: AsyncClient, payload: dict, expected: str
) -> None:
    campaign_id = await _draft_campaign(client)
    await client.patch(f"/api/campaigns/{campaign_id}", json=payload)

    response = await client.post(f"/api/campaigns/{campaign_id}/concepts/generate")
    assert response.status_code == 422
    assert response.json()["message_fa"] == expected
