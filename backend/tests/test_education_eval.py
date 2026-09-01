"""
The educational smoke harness itself.

The property that matters most: running it without --live must never reach a
paid provider.
"""

import os
from pathlib import Path

import pytest

from app.providers.education import set_educational_agent
from app.providers.image import set_image_provider
from scripts.education_eval.cases import case_ids, load_cases
from scripts.education_eval.cli import main
from scripts.education_eval.runner import run_case, write_json


@pytest.fixture(autouse=True)
def _reset_providers():
    yield
    set_educational_agent(None)
    set_image_provider(None)


def test_six_representative_fixtures_are_available() -> None:
    cases = load_cases()
    assert len(cases) >= 6
    ids = set(case_ids())
    # Persian maths, Persian science, English, playful, formal, theme reuse.
    assert {
        "fa_math_decimals",
        "fa_science_water_cycle",
        "en_photosynthesis",
        "fa_playful_alphabet",
        "fa_formal_exam_prep",
        "fa_theme_reuse_fractions",
    } <= ids
    assert all(case.user_prompt.strip() for case in cases)


def test_the_theme_reuse_fixture_carries_a_theme_and_nothing_post_specific() -> None:
    case = next(item for item in load_cases() if item.id == "fa_theme_reuse_fractions")
    assert case.theme is not None
    assert case.theme["palette"]["primary"]
    for key in ("headline", "final_prompt", "visual_plan", "content", "typography"):
        assert key not in case.theme


async def test_a_case_runs_agent_then_one_image(tmp_path: Path) -> None:
    case = next(item for item in load_cases() if item.id == "fa_math_decimals")
    outcome, detail = await run_case(case)

    assert outcome.ok, outcome.errors
    assert outcome.language == "fa"
    assert outcome.image_count == 1
    assert outcome.image_bytes > 0
    assert outcome.prompt_chars > 0
    assert detail["agent"]["validation"]["ok"] is True
    assert detail["agent"]["final_prompt"]
    assert "content" not in detail["agent"]
    assert detail["render_spec"]["render_mode"] == "educational"
    assert "text_layers" not in detail["render_spec"]
    assert "cta_fa" not in detail["render_spec"]


async def test_no_image_mode_skips_the_image_call() -> None:
    case = next(item for item in load_cases() if item.id == "en_photosynthesis")
    outcome, detail = await run_case(case, with_image=False)

    assert outcome.ok, outcome.errors
    assert outcome.image_count == 0
    assert "image" not in detail


async def test_language_mismatch_is_reported_as_a_failure() -> None:
    case = next(item for item in load_cases() if item.id == "en_photosynthesis")
    lying = type(case)(
        id=case.id,
        label=case.label,
        user_prompt=case.user_prompt,
        expect_language="fa",
    )
    outcome, _ = await run_case(lying, with_image=False)
    assert not outcome.ok
    assert any("expected language fa" in error for error in outcome.errors)


def test_default_run_forces_stub_providers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    A developer's .env may point at real OpenRouter. Without --live the harness
    must override that, or a smoke run silently spends money.
    """
    monkeypatch.setenv("CONTENT_PROVIDER", "openrouter")
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")

    exit_code = main(
        ["--case", "fa_math_decimals", "--out", str(tmp_path / "run")]
    )

    assert exit_code == 0
    assert os.environ["CONTENT_PROVIDER"] == "stub"
    assert os.environ["IMAGE_PROVIDER"] == "stub"


def test_write_json_round_trips_persian(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out.json"
    write_json(target, {"headline": "مأموریت نجات ممیز کوچولو"})
    text = target.read_text(encoding="utf-8")
    # ensure_ascii=False, so Persian stays readable in the artifact.
    assert "مأموریت" in text
