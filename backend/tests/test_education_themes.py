"""
The theme system: built-ins, saving a generated theme, and reusing it.

The rule under test throughout is that a theme is a reusable visual system, not
a copy of the post it came from.
"""

import uuid

from httpx import AsyncClient

from app.content.education_themes import builtin_theme_ids
from app.services.education.themes import POST_ONLY_KEYS, sanitize_theme
from tests.conftest import InMemoryStorage, auth_header

PROMPT = "یک پست درباره کسرهای مساوی برای کلاس ششم بساز"
SECOND_PROMPT = "یک پست درباره ضرب اعداد دو رقمی بساز"


async def _ready_post(
    client: AsyncClient, user_id: uuid.UUID, *, prompt: str = PROMPT, **body: object
) -> dict:
    created = await client.post(
        "/api/education/posts",
        json={"user_prompt": prompt, **body},
        headers=auth_header(user_id),
    )
    assert created.status_code == 200, created.text
    post_id = created.json()["id"]
    status = await client.get(
        f"/api/education/posts/{post_id}/status", headers=auth_header(user_id)
    )
    assert status.json()["status"] == "ready", status.text
    detail = await client.get(
        f"/api/education/posts/{post_id}", headers=auth_header(user_id)
    )
    return detail.json()


async def test_builtin_themes_are_listed_without_signing_in(
    client: AsyncClient,
) -> None:
    """The picker has to render before the signup gate."""
    response = await client.get("/api/education/themes")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["builtin"]] == list(builtin_theme_ids())
    assert body["saved"] == []
    # Backend-only creative guidance never reaches the browser.
    assert all("creative_guidance" not in item for item in body["builtin"])


async def test_no_theme_selected_means_the_agent_designs_one(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    post = await _ready_post(client, uuid.uuid4())
    assert post["selected_theme_id"] is None
    assert post["selected_builtin_theme_id"] is None
    theme = post["theme_json"]
    assert theme["name"]
    assert theme["palette"]["primary"]
    assert theme["illustration_style"]
    assert theme["mood"]
    assert "typography" not in theme


async def test_a_builtin_theme_reaches_the_agent_as_style_only(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    post = await _ready_post(client, user_id, builtin_theme_id="chalkboard")
    assert post["selected_builtin_theme_id"] == "chalkboard"
    theme = post["theme_json"]
    # Chalkboard's own palette and look survived, rather than the default.
    assert "#f8fafc" in theme["palette"]["primary"]
    assert "chalk" in theme["illustration_style"].lower()
    assert theme["mood"]
    assert "typography" not in theme
    spec = post["render_spec_json"]
    assert spec["render_mode"] == "educational"
    assert "text_layers" not in spec
    assert "cta_fa" not in spec
    assert "headline_fa" not in spec


async def test_saved_theme_keeps_the_look_and_drops_the_post(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    post = await _ready_post(client, user_id)

    saved = await client.post(
        "/api/education/themes",
        json={"post_id": post["id"]},
        headers=auth_header(user_id),
    )
    assert saved.status_code == 200, saved.text
    row = saved.json()
    assert row["source"] == "user"
    # Defaults to the agent's own suggestion, so there is no naming form.
    assert row["name"] == post["theme_json"]["name"]

    theme = row["theme_json"]
    assert theme["palette"]["primary"]
    assert theme["illustration_style"]
    assert theme["mood"]
    assert "typography" not in theme
    for key in POST_ONLY_KEYS:
        assert key not in theme, f"{key} must not survive into a saved theme"
    assert post["headline"] not in str(theme)
    assert post["agent_json"]["final_prompt"] not in str(theme)


async def test_a_saved_theme_can_be_reused_on_a_different_topic(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    """Consistent look, different lesson: the point of the theme system."""
    user_id = uuid.uuid4()
    first = await _ready_post(client, user_id)
    saved = await client.post(
        "/api/education/themes",
        json={"post_id": first["id"], "name": "ریاضی ششم - بنفش سه‌بعدی"},
        headers=auth_header(user_id),
    )
    theme_id = saved.json()["id"]

    second = await _ready_post(
        client, user_id, prompt=SECOND_PROMPT, theme_id=theme_id
    )
    assert second["selected_theme_id"] == theme_id
    assert second["user_prompt"] == SECOND_PROMPT
    # Same visual system...
    assert (
        second["theme_json"]["palette"]["primary"]
        == saved.json()["theme_json"]["palette"]["primary"]
    )
    assert (
        second["theme_json"]["illustration_style"]
        == saved.json()["theme_json"]["illustration_style"]
    )
    assert second["theme_json"]["mood"] == saved.json()["theme_json"]["mood"]
    # ...but its own image, not a duplicate of the first post's.
    assert second["image_storage_path"] != first["image_storage_path"]


async def test_saved_themes_are_owner_scoped(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    post = await _ready_post(client, owner)
    saved = await client.post(
        "/api/education/themes",
        json={"post_id": post["id"]},
        headers=auth_header(owner),
    )
    theme_id = saved.json()["id"]

    listed = await client.get("/api/education/themes", headers=auth_header(stranger))
    assert listed.json()["saved"] == []

    renamed = await client.patch(
        f"/api/education/themes/{theme_id}",
        json={"name": "دزدیده‌شده"},
        headers=auth_header(stranger),
    )
    assert renamed.status_code == 403

    removed = await client.delete(
        f"/api/education/themes/{theme_id}", headers=auth_header(stranger)
    )
    assert removed.status_code == 403

    mine = await client.get("/api/education/themes", headers=auth_header(owner))
    assert [item["id"] for item in mine.json()["saved"]] == [theme_id]


async def test_a_stranger_theme_id_is_ignored_rather_than_borrowed(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    post = await _ready_post(client, owner)
    saved = await client.post(
        "/api/education/themes",
        json={"post_id": post["id"]},
        headers=auth_header(owner),
    )
    theme_id = saved.json()["id"]

    # The stranger names someone else's theme. Generation still succeeds, but
    # with a freshly designed theme rather than the borrowed one.
    theirs = await _ready_post(client, stranger, theme_id=theme_id)
    assert theirs["theme_json"]["palette"]["primary"]


async def test_themes_can_be_renamed_and_deleted(
    client: AsyncClient, storage: InMemoryStorage
) -> None:
    user_id = uuid.uuid4()
    post = await _ready_post(client, user_id)
    saved = await client.post(
        "/api/education/themes",
        json={"post_id": post["id"]},
        headers=auth_header(user_id),
    )
    theme_id = saved.json()["id"]

    renamed = await client.patch(
        f"/api/education/themes/{theme_id}",
        json={"name": "تم تازه"},
        headers=auth_header(user_id),
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "تم تازه"
    assert renamed.json()["theme_json"]["name"] == "تم تازه"

    removed = await client.delete(
        f"/api/education/themes/{theme_id}", headers=auth_header(user_id)
    )
    assert removed.status_code == 204
    listed = await client.get("/api/education/themes", headers=auth_header(user_id))
    assert listed.json()["saved"] == []


async def test_anonymous_callers_cannot_save_a_theme(client: AsyncClient) -> None:
    response = await client.post(
        "/api/education/themes", json={"post_id": str(uuid.uuid4())}
    )
    assert response.status_code == 403


def test_sanitize_drops_post_content_and_normalizes_fonts() -> None:
    raw = {
        "name": "تم من",
        "palette": {"primary": ["#123456", "not-a-color"], "secondary": []},
        "illustration_style": "clay",
        "shape_language": "round",
        "decorative_motifs": ["stars", ""],
        "mood": "playful",
        "lighting": "soft",
        "typography": {"headline_font_id": "comic-sans", "body_font_id": "amiri"},
        "cta_fa": "شروع",
        "text_layers": [{"text": "امتیاز 100"}],
        # All of this belongs to one post and must be discarded.
        "headline": "مأموریت نجات ممیز کوچولو",
        "final_prompt": "a very specific image prompt",
        "visual_plan": {"scene": "one particular scene"},
        "language": "fa",
    }
    cleaned = sanitize_theme(raw)

    assert cleaned["palette"]["primary"] == ["#123456"]
    assert cleaned["decorative_motifs"] == ["stars"]
    assert cleaned["mood"] == "playful"
    assert "typography" not in cleaned
    assert "cta_fa" not in cleaned
    assert "text_layers" not in cleaned
    for key in POST_ONLY_KEYS:
        assert key not in cleaned
