"""Signed URL issuance, and the ownership check behind it."""

import uuid

from httpx import AsyncClient

from tests.conftest import auth_header, png_bytes


async def _campaign_with_image(client: AsyncClient) -> tuple[str, str]:
    campaign_id = (await client.post("/api/campaigns", json={})).json()["id"]
    uploaded = await client.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("a.png", png_bytes(), "image/png"))],
    )
    return campaign_id, uploaded.json()[0]["storage_path"]


async def test_owner_receives_a_signed_url(client: AsyncClient, storage) -> None:
    _, path = await _campaign_with_image(client)

    response = await client.post("/api/assets/resolve", json={"paths": [path]})
    assert response.status_code == 200
    assert response.json()[path].startswith("https://storage.test/product-images/")


async def test_bundled_assets_resolve_without_signing(client: AsyncClient) -> None:
    response = await client.post(
        "/api/assets/resolve", json={"paths": ["public://mock/product-saffron.svg"]}
    )
    assert response.json() == {
        "public://mock/product-saffron.svg": "/mock/product-saffron.svg"
    }


async def test_holding_a_path_is_not_enough(client: AsyncClient, storage) -> None:
    """A path is not a capability: ownership is re-derived from the object key."""
    _, path = await _campaign_with_image(client)

    stranger = AsyncClient(transport=client._transport, base_url="http://api.test")
    async with stranger:
        response = await stranger.post("/api/assets/resolve", json={"paths": [path]})

    assert response.status_code == 200
    assert response.json() == {path: None}


async def test_forged_paths_are_denied(client: AsyncClient, storage) -> None:
    forged = f"supabase://product-images/campaigns/{uuid.uuid4()}/products/x.png"
    nonsense = "supabase://product-images/../../etc/passwd"

    response = await client.post(
        "/api/assets/resolve",
        headers=auth_header(uuid.uuid4()),
        json={"paths": [forged, nonsense]},
    )
    assert response.json() == {forged: None, nonsense: None}


async def test_resolution_is_batched(client: AsyncClient, storage) -> None:
    campaign_id, first = await _campaign_with_image(client)
    second = (
        await client.post(
            f"/api/campaigns/{campaign_id}/images",
            files=[("files", ("b.png", png_bytes(), "image/png"))],
        )
    ).json()[0]["storage_path"]

    response = await client.post(
        "/api/assets/resolve",
        json={"paths": [first, second, "public://mock/product-saffron.svg"]},
    )
    assert len(response.json()) == 3
    assert all(response.json().values())
