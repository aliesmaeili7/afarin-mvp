"""Text-on-image layers persist on AssetRenderSpec without an image call."""

import uuid

from httpx import AsyncClient

from app.services.campaigns import text_layers as type_layers
from tests.conftest import auth_header, png_bytes


def _layer(**overrides) -> dict:
    base = {
        "id": "role-headline",
        "role": "headline",
        "text": "آرام و جسور",
        "x": 0.1,
        "y": 0.7,
        "width": 0.8,
        "font_family": "vazirmatn",
        "font_size": 0.076,
        "font_weight": 700,
        "color": "#ffffff",
        "text_align": "center",
        "opacity": 1,
        "background": "none",
        "background_color": None,
        "background_opacity": 0.55,
        "shadow": True,
    }
    return {**base, **overrides}


async def _ready(client: AsyncClient, headers: dict[str, str]) -> str:
    campaign_id = (
        await client.post("/api/campaigns", json={}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/api/campaigns/{campaign_id}/images",
        headers=headers,
        files=[("files", ("product.png", png_bytes(), "image/png"))],
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/product",
        headers=headers,
        json={"name": "شال نخی"},
    )
    await client.patch(
        f"/api/campaigns/{campaign_id}",
        headers=headers,
        json={"objective": "promotion", "visual_style": "friendly"},
    )
    await client.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    await client.get(f"/api/campaigns/{campaign_id}/status", headers=headers)
    return campaign_id


def _assets(detail: dict) -> dict[str, dict]:
    return {
        row["asset_type"]: row
        for row in detail["assets"]
        if row["asset_type"] != "generated_background"
    }


def test_parse_rejects_an_eleventh_layer() -> None:
    layers = [_layer(id=f"n-{index}", role="custom") for index in range(11)]
    try:
        type_layers.parse_text_layers(layers)
        raised = False
    except Exception:
        raised = True
    assert raised


def test_legacy_spec_survives_without_text_layers() -> None:
    spec = {"headline_fa": "سلام", "cta_fa": "بخر"}
    cleared = type_layers.apply_text_layers(spec, None)
    assert "text_layers" not in cleared
    assert cleared["headline_fa"] == "سلام"


async def test_materialize_omits_text_layers(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    feed = _assets(detail.json())["feed_final"]
    assert "text_layers" not in feed["metadata_json"]
    assert feed["metadata_json"]["headline_fa"]


async def test_patch_persists_on_one_asset_only(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    detail = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assets = _assets(detail.json())
    feed = assets["feed_final"]
    story = assets["story_final"]

    layers = [
        _layer(x=0.2, y=0.55, font_size=0.09, color="#e9b44c", font_family="amiri")
    ]
    patched = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": layers},
    )
    assert patched.status_code == 200
    spec = patched.json()["metadata_json"]
    assert spec["text_layers"][0]["x"] == 0.2
    assert spec["text_layers"][0]["y"] == 0.55
    assert spec["text_layers"][0]["font_size"] == 0.09
    assert spec["text_layers"][0]["color"] == "#e9b44c"
    assert spec["text_layers"][0]["font_family"] == "amiri"
    assert spec["headline_fa"] == "آرام و جسور"

    reloaded = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    again = _assets(reloaded.json())
    assert again["feed_final"]["metadata_json"]["text_layers"][0]["x"] == 0.2
    assert "text_layers" not in again["story_final"]["metadata_json"]
    assert again["story_final"]["id"] == story["id"]


async def test_added_layer_persists_and_eleventh_is_rejected(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]

    custom = _layer(id="custom-1", role="custom", text="ارسال رایگان", y=0.4)
    ok = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": [_layer(), custom]},
    )
    assert ok.status_code == 200
    assert len(ok.json()["metadata_json"]["text_layers"]) == 2

    too_many = [_layer(id=f"n-{index}", role="custom") for index in range(11)]
    refused = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": too_many},
    )
    assert refused.status_code == 422
    assert refused.json()["message_fa"] == "حداکثر ۱۰ متن می‌تونی به این تصویر اضافه کنی."


async def test_optional_layer_can_be_removed(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]
    layers = [
        _layer(),
        _layer(id="role-cta", role="cta", text="بخر", y=0.88, background="pill"),
    ]
    await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": layers},
    )
    remaining = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": [_layer()]},
    )
    roles = [row["role"] for row in remaining.json()["metadata_json"]["text_layers"]]
    assert roles == ["headline"]


async def test_null_text_layers_restores_legacy_layout(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]
    await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": [_layer()]},
    )
    reset = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": None},
    )
    assert reset.status_code == 200
    assert "text_layers" not in reset.json()["metadata_json"]
    assert reset.json()["metadata_json"]["headline_fa"] == "آرام و جسور"


async def test_stranger_cannot_patch_layers(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]

    stranger = auth_header(uuid.uuid4())
    response = await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=stranger,
        json={"text_layers": [_layer()]},
    )
    assert response.status_code == 403
    assert response.json()["message_fa"] == "دسترسی به این کمپین برای شما مجاز نیست."


async def test_rewrite_updates_role_text_not_position(
    client: AsyncClient, storage
) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]
    await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": [_layer(x=0.33, y=0.61)]},
    )
    rewritten = await client.post(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}/rewrite",
        headers=headers,
        json={"intent": "new_headline"},
    )
    assert rewritten.status_code == 200
    layer = rewritten.json()["metadata_json"]["text_layers"][0]
    assert layer["x"] == 0.33
    assert layer["y"] == 0.61
    assert layer["text"] != "آرام و جسور"


async def test_scene_regen_keeps_text_layers(client: AsyncClient, storage) -> None:
    headers = auth_header(uuid.uuid4())
    await client.post("/api/session/adopt", headers=headers)
    campaign_id = await _ready(client, headers)
    feed = _assets(
        (await client.get(f"/api/campaigns/{campaign_id}", headers=headers)).json()
    )["feed_final"]
    await client.patch(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}",
        headers=headers,
        json={"text_layers": [_layer(x=0.15)]},
    )
    regen = await client.post(
        f"/api/campaigns/{campaign_id}/assets/{feed['id']}/regenerate",
        headers=headers,
    )
    assert regen.status_code == 200
    spec = regen.json()["metadata_json"]
    assert spec["text_layers"][0]["x"] == 0.15
    assert spec["scene_image_path"]
