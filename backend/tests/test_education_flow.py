"""
The educational path end to end: one prompt in, one square post out.

These run entirely on stub providers, so the suite never spends money.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import EducationalPost, GenerationJob
from app.db.session import get_sessionmaker
from app.services.education.render_spec import (
    AD_COMPOSITION_KEYS,
    RENDER_MODE_EDUCATIONAL,
    is_educational_render_spec,
)
from tests.conftest import InMemoryStorage, auth_header

FA_PROMPT = (
    "برای کلاس ششم یک پست جذاب درباره مرور اعداد اعشاری بساز. "
    "می‌خواهم مثل یک بازی ماجراجویی باشد و شخصیت اصلی ممیز کوچولو باشد."
)
EN_PROMPT = "Make a playful post for grade 6 reviewing decimals like 0.5 and 1.25."


async def _create(
    client: AsyncClient,
    user_id: uuid.UUID,
    *,
    prompt: str = FA_PROMPT,
    **body: object,
) -> dict:
    response = await client.post(
        "/api/education/posts",
        json={"user_prompt": prompt, **body},
        headers=auth_header(user_id),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _run(client: AsyncClient, user_id: uuid.UUID, post_id: str) -> dict:
    status = await client.get(
        f"/api/education/posts/{post_id}/status", headers=auth_header(user_id)
    )
    assert status.status_code == 200, status.text
    return status.json()


async def test_one_prompt_is_the_only_required_input(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    """No subject, grade, audience, tone or title fields are needed."""
    user_id = uuid.uuid4()
    created = await _create(client, user_id)
    assert created["status"] == "queued"
    assert created["selected_theme_id"] is None
    assert created["selected_builtin_theme_id"] is None

    status = await _run(client, user_id, created["id"])
    assert status["status"] == "ready"
    assert status["percent"] == 100

    detail = await client.get(
        f"/api/education/posts/{created['id']}", headers=auth_header(user_id)
    )
    post = detail.json()
    assert post["status"] == "ready"
    assert post["headline"]
    assert post["image_storage_path"].startswith("supabase://")
    assert f"education/{created['id']}/" in post["image_storage_path"]
    spec = post["render_spec_json"]
    assert spec["render_mode"] == RENDER_MODE_EDUCATIONAL
    assert spec["image_path"] == post["image_storage_path"]
    assert is_educational_render_spec(spec)
    for key in AD_COMPOSITION_KEYS:
        assert key not in spec
    agent = post["agent_json"]
    assert agent["final_prompt"]
    assert "content" not in agent
    assert "overlay_items" not in agent
    assert "visual_plan" not in agent


async def test_prompt_language_drives_the_output_language(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    persian = await _create(client, user_id, prompt=FA_PROMPT)
    await _run(client, user_id, persian["id"])
    english = await _create(client, user_id, prompt=EN_PROMPT)
    await _run(client, user_id, english["id"])

    fa = (
        await client.get(
            f"/api/education/posts/{persian['id']}", headers=auth_header(user_id)
        )
    ).json()
    en = (
        await client.get(
            f"/api/education/posts/{english['id']}", headers=auth_header(user_id)
        )
    ).json()

    assert fa["language"] == "fa"
    assert en["language"] == "en"
    fa_prompt = fa["agent_json"]["final_prompt"]
    en_prompt = en["agent_json"]["final_prompt"]
    assert any("\u0600" <= ch <= "\u06ff" for ch in fa_prompt)
    assert not any("\u0600" <= ch <= "\u06ff" for ch in en_prompt)


async def test_educational_result_has_no_overlay_or_ad_copy_fields(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    """
    Exact wording belongs in the image prompt. The stored post must not grow
    AdCanvas layers, CTAs, badges or advertising copy fields.
    """
    user_id = uuid.uuid4()
    created = await _create(
        client,
        user_id,
        prompt="A post about reviewing decimals 0.5 and 1.25. Title: Place Value.",
    )
    await _run(client, user_id, created["id"])
    post = (
        await client.get(
            f"/api/education/posts/{created['id']}", headers=auth_header(user_id)
        )
    ).json()

    assert "Place Value" in post["agent_json"]["final_prompt"]
    assert "0.5" in post["agent_json"]["final_prompt"]
    spec = post["render_spec_json"]
    assert spec.get("text_layers") in (None, [])
    assert "text_layers" not in spec
    assert spec.get("cta_fa") is None
    assert "cta_fa" not in spec
    assert "headline_fa" not in spec
    assert "price_text" not in spec
    assert "brand_name" not in spec
    assert post["theme_json"].get("typography") is None


async def test_text_overlay_endpoint_is_gone(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    created = await _create(client, user_id)
    await _run(client, user_id, created["id"])
    patched = await client.patch(
        f"/api/education/posts/{created['id']}/text",
        json={"text_layers": [{"role": "headline", "text": "عنوان"}]},
        headers=auth_header(user_id),
    )
    assert patched.status_code in (404, 405)


async def test_exactly_one_agent_call_and_one_image_are_recorded(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    created = await _create(client, user_id)
    await _run(client, user_id, created["id"])

    async with get_sessionmaker()() as session:
        rows = list(
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.educational_post_id == uuid.UUID(created["id"])
                )
            )
        )
    by_type = {row.job_type: row for row in rows}
    assert set(by_type) == {"educational_agent", "educational_image"}
    assert all(row.status == "succeeded" for row in rows)
    assert all(row.campaign_id is None for row in rows)
    assert by_type["educational_image"].output_json["output_count"] == 1
    assert by_type["educational_image"].input_json["model"] == "openai/gpt-image-2"
    assert by_type["educational_image"].model == "openai/gpt-image-2"
    assert by_type["educational_image"].actual_cost_usd is not None
    # Exactly one stored object: no second image, no Story, no carousel.
    assert len(storage.objects) == 1


async def test_wall_time_is_measured_not_summed_from_providers(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    created = await _create(client, user_id)
    await _run(client, user_id, created["id"])

    async with get_sessionmaker()() as session:
        post = await session.get(EducationalPost, uuid.UUID(created["id"]))
        jobs = list(
            await session.scalars(
                select(GenerationJob).where(
                    GenerationJob.educational_post_id == uuid.UUID(created["id"])
                )
            )
        )
    assert post is not None
    assert post.wall_time_ms is not None and post.wall_time_ms >= 0
    summed = sum(job.latency_ms or 0 for job in jobs)
    # The stub image provider reports 1ms, so a summed total could never match
    # real elapsed time. This is the guard against reintroducing that bug.
    assert post.wall_time_ms != summed or summed == 0


async def test_anonymous_callers_cannot_create_or_read_posts(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    anonymous = await client.post(
        "/api/education/posts", json={"user_prompt": FA_PROMPT}
    )
    assert anonymous.status_code == 403

    async with get_sessionmaker()() as session:
        count = len(list(await session.scalars(select(EducationalPost))))
    assert count == 0


async def test_a_stranger_cannot_read_or_delete_someone_elses_post(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    created = await _create(client, owner)

    read = await client.get(
        f"/api/education/posts/{created['id']}", headers=auth_header(stranger)
    )
    assert read.status_code == 403

    removed = await client.delete(
        f"/api/education/posts/{created['id']}", headers=auth_header(stranger)
    )
    assert removed.status_code == 403

    mine = await client.get("/api/education/posts", headers=auth_header(stranger))
    assert mine.json() == []


async def test_empty_prompt_is_rejected_before_any_provider_call(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    response = await client.post(
        "/api/education/posts",
        json={"user_prompt": "   "},
        headers=auth_header(user_id),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert len(storage.objects) == 0


async def test_generated_image_is_readable_only_by_its_owner(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    created = await _create(client, owner)
    await _run(client, owner, created["id"])
    post = (
        await client.get(
            f"/api/education/posts/{created['id']}", headers=auth_header(owner)
        )
    ).json()
    path = post["image_storage_path"]

    allowed = await client.post(
        "/api/assets/resolve", json={"paths": [path]}, headers=auth_header(owner)
    )
    assert allowed.json()[path] is not None

    denied = await client.post(
        "/api/assets/resolve", json={"paths": [path]}, headers=auth_header(stranger)
    )
    assert denied.json()[path] is None

    anonymous = await client.post("/api/assets/resolve", json={"paths": [path]})
    assert anonymous.json()[path] is None


@pytest.mark.parametrize("status_code", [403])
async def test_status_polling_requires_ownership(
    client: AsyncClient, storage: InMemoryStorage, status_code: int
) -> None:
    owner = uuid.uuid4()
    created = await _create(client, owner)
    response = await client.get(
        f"/api/education/posts/{created['id']}/status",
        headers=auth_header(uuid.uuid4()),
    )
    assert response.status_code == status_code
