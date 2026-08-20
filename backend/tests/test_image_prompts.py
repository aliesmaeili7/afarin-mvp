from types import SimpleNamespace

from app.providers.image.prompts import HARD_NEGATIVES, build_scene_prompt


def test_scene_prompt_is_an_empty_set_with_no_text() -> None:
    concept = SimpleNamespace(
        visual_direction="soft spotlight, deep shadows",
        background_prompt="dark velvet studio backdrop, no text",
    )
    campaign = SimpleNamespace(visual_style="luxury")
    prompt = build_scene_prompt(concept, campaign)

    lowered = prompt.lower()
    assert "no text" in lowered
    assert "no product" in lowered
    assert "no packaging" in lowered
    assert "no logos" in lowered
    for negative in HARD_NEGATIVES:
        assert negative in prompt
    assert prompt.rstrip().endswith("no text") or "no text" in lowered


def test_scene_prompt_does_not_describe_the_sku() -> None:
    concept = SimpleNamespace(
        visual_direction="warm daylight",
        background_prompt="empty marble counter, morning light",
    )
    campaign = SimpleNamespace(visual_style="minimal")
    prompt = build_scene_prompt(concept, campaign)
    assert "زعفران" not in prompt
    assert "packshot" not in prompt.lower()


def test_variation_changes_the_prompt() -> None:
    concept = SimpleNamespace(visual_direction="glow", background_prompt="studio")
    campaign = SimpleNamespace(visual_style="bold")
    first = build_scene_prompt(concept, campaign, variation=0)
    second = build_scene_prompt(concept, campaign, variation=2)
    assert "variation 2" in second
    assert first != second
