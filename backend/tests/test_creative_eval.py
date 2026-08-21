"""Internal creative eval harness. Stub providers only — never paid."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.providers.image.base import ImageApiError, ImageRequest
from app.providers.image.creative_prompts import (
    CREATIVE_PROMPT_VERSION,
    build_creative_prompt,
)
from app.providers.image.stub import StubImageProvider
from app.providers.vision.base import PlannerContext
from app.providers.vision.stub import StubVisualPlanner
from app.services.campaigns.creative_core import generate_recipe_set
from app.services.campaigns.recipes import recipe_from_ids
from scripts.creative_eval.cases import (
    FixtureError,
    catalog_recipes,
    load_case,
    parse_recipes,
    validate_case,
)
from scripts.creative_eval.cli import main
from scripts.creative_eval.plan import build_plan
from scripts.creative_eval.ratings import load_ratings, recipe_summaries, save_ratings
from scripts.creative_eval.runner import (
    execute_run,
    planner_context,
    recipes_from_fixture,
)
from scripts.creative_eval.sanitize import sanitize
from scripts.creative_eval.store import allocate_run_dir
from tests.fakes import FakeImageProvider


class CountingPlanner(StubVisualPlanner):
    def __init__(self) -> None:
        self.plan_calls = 0
        self.score_calls = 0

    async def plan_directions(self, image, context):
        self.plan_calls += 1
        return await super().plan_directions(image, context)

    async def score_candidates(self, reference, candidates, context):
        self.score_calls += 1
        return await super().score_candidates(reference, candidates, context)


def test_fixture_validation_and_recipe_parse() -> None:
    case = load_case("sweatshirt_01")
    assert case["case_id"] == "sweatshirt_01"
    assert case["objective"] == "sell_product"
    assert case["visual_style"] == "friendly"
    parsed = parse_recipes(
        "fashion_editorial:model_using,anime:illustrated_scene"
    )
    assert parsed == [
        {"style_id": "fashion_editorial", "template_id": "model_using"},
        {"style_id": "anime", "template_id": "illustrated_scene"},
    ]
    with pytest.raises(FixtureError):
        parse_recipes("not-a-recipe")
    with pytest.raises(FixtureError):
        parse_recipes("anime:not_a_template")
    with pytest.raises(FixtureError):
        catalog_recipes(
            all_styles=True,
            all_templates=True,
            style_id="photoreal_commercial",
            template_id="hero_product",
        )
    styles = catalog_recipes(
        all_styles=True,
        all_templates=False,
        style_id=None,
        template_id="hero_product",
    )
    assert len(styles) == 14
    templates = catalog_recipes(
        all_styles=False,
        all_templates=True,
        style_id="photoreal_commercial",
        template_id=None,
    )
    assert len(templates) == 12


def test_fixture_rejects_unknown_objective(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "case_id": "bad",
                "product_image": "x.jpg",
                "product": {"name": "x"},
                "objective": "go_viral",
                "visual_style": "friendly",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(FixtureError):
        validate_case(json.loads(path.read_text()), path=path)


def test_production_prompt_builder_is_reused() -> None:
    recipe = recipe_from_ids(
        "fashion_editorial", "model_using", source="eval_fixed"
    )
    campaign = SimpleNamespace(visual_style="friendly")
    concept = SimpleNamespace(visual_direction="")
    expected = build_creative_prompt(concept, campaign, recipe, variation=0)

    async def run() -> None:
        result = await generate_recipe_set(
            recipe=recipe,
            reference=_tiny_ref(),
            campaign=campaign,
            concept=concept,
            planner_context=PlannerContext(
                product_name="هودی",
                description=None,
                brand_name=None,
                price_text=None,
                audience=None,
                objective="sell_product",
                visual_style="friendly",
            ),
            provider=StubImageProvider(),
            planner=None,
            n=1,
        )
        assert result.prompt == expected
        assert result.prompt_version == CREATIVE_PROMPT_VERSION

    import asyncio

    asyncio.run(run())


def test_run_dir_never_overwrites(tmp_path: Path) -> None:
    first = allocate_run_dir(case_id="sweatshirt_01", label="a", runs_dir=tmp_path)
    second = allocate_run_dir(case_id="sweatshirt_01", label="a", runs_dir=tmp_path)
    assert first != second
    assert first.is_dir() and second.is_dir()
    assert "sweatshirt_01" in first.name


def test_sanitized_metadata_has_no_api_keys() -> None:
    payload = {
        "Authorization": "Bearer sk-abcdefghi",
        "openrouter_api_key": "sk-live-secretvalue",
        "prompt": "hello data:image/png;base64,AAAA",
        "nested": {"api_key": "sk-zzzzzzzz"},
    }
    cleaned = sanitize(payload)
    blob = json.dumps(cleaned)
    assert "sk-" not in blob
    assert "AAAA" not in blob
    assert cleaned["Authorization"] == "[redacted]"
    assert cleaned["openrouter_api_key"] == "[redacted]"


def test_paid_run_cannot_happen_accidentally(tmp_path: Path) -> None:
    code = main(
        [
            "--case",
            "sweatshirt_01",
            "--mode",
            "fixed",
            "--provider",
            "openrouter",
            "--candidates",
            "1",
        ]
    )
    assert code == 2


def test_catalog_sweep_requires_confirm() -> None:
    code = main(
        [
            "--case",
            "sweatshirt_01",
            "--mode",
            "fixed",
            "--all-styles",
            "--template",
            "hero_product",
            "--provider",
            "openrouter",
            "--paid",
        ]
    )
    assert code == 2


def test_dry_run_makes_no_provider_calls() -> None:
    code = main(
        [
            "--case",
            "sweatshirt_01",
            "--mode",
            "fixed",
            "--dry-run",
            "--provider",
            "openrouter",
            "--paid",
        ]
    )
    assert code == 0


@pytest.mark.asyncio
async def test_fixed_mode_does_not_call_director(tmp_path: Path) -> None:
    case = load_case("sweatshirt_01")
    planner = CountingPlanner()
    images = FakeImageProvider()
    plan = build_plan(
        case_id=case["case_id"],
        mode="fixed",
        recipes=case["fixed_recipes"],
        candidates=1,
        quality_check=False,
        repair="none",
        story=False,
        master_crop=False,
        provider="stub",
        paid=False,
        label="test",
    )
    recipes = recipes_from_fixture(case, case["fixed_recipes"])
    run_dir = await execute_run(
        case=case,
        plan=plan,
        provider=images,
        planner=planner,
        recipes=recipes,
        directions=None,
        director=None,
        runs_dir=tmp_path,
    )
    assert planner.plan_calls == 0
    assert (run_dir / "run_meta.json").is_file()
    assert not (run_dir / "director_output.json").exists()
    assert len(list((run_dir / "recipes").iterdir())) == 3
    assert images.calls
    assert all(call.references for call in images.calls)


@pytest.mark.asyncio
async def test_director_mode_calls_director_once(tmp_path: Path) -> None:
    case = load_case("sweatshirt_01")
    planner = CountingPlanner()
    image = Path(case["_image_path"]).read_bytes()
    result = await planner.plan_directions(image, planner_context(case))
    assert planner.plan_calls == 1
    from scripts.creative_eval.runner import recipes_from_director

    recipes = recipes_from_director(result)
    plan = build_plan(
        case_id=case["case_id"],
        mode="director",
        recipes=[
            {"style_id": r["style_id"], "template_id": r["template_id"]}
            for r in recipes
        ],
        candidates=1,
        quality_check=False,
        repair="none",
        story=False,
        master_crop=False,
        provider="stub",
        paid=False,
        label=None,
    )
    run_dir = await execute_run(
        case=case,
        plan=plan,
        provider=StubImageProvider(),
        planner=planner,
        recipes=recipes,
        directions=list(result.directions),
        director=result,
        runs_dir=tmp_path,
    )
    assert planner.plan_calls == 1
    assert (run_dir / "director_output.json").is_file()
    payload = json.loads((run_dir / "director_output.json").read_text())
    assert len(payload["directions"]) == 3


@pytest.mark.asyncio
async def test_partial_provider_failure_still_creates_run(tmp_path: Path) -> None:
    case = load_case("sweatshirt_01")
    boom = ImageApiError(
        status_code=500,
        provider_message="upstream failed",
        payload_keys=("prompt",),
        retryable=False,
    )
    ok = await StubImageProvider().generate(
        ImageRequest(prompt="x", aspect_ratio="4:5", n=1)
    )
    images = FakeImageProvider([ok, boom, ok])
    plan = build_plan(
        case_id=case["case_id"],
        mode="fixed",
        recipes=case["fixed_recipes"],
        candidates=1,
        quality_check=False,
        repair="none",
        story=False,
        master_crop=False,
        provider="stub",
        paid=False,
        label=None,
        concurrency=1,
    )
    run_dir = await execute_run(
        case=case,
        plan=plan,
        provider=images,
        planner=CountingPlanner(),
        recipes=recipes_from_fixture(case, case["fixed_recipes"]),
        directions=None,
        director=None,
        runs_dir=tmp_path,
    )
    errors = list(run_dir.glob("recipes/*/error.json"))
    ok_images = list(run_dir.glob("recipes/*/candidate-1.jpg"))
    assert errors
    assert ok_images
    meta = json.loads((run_dir / "run_meta.json").read_text())
    assert meta["run_id"] == run_dir.name


def test_human_ratings_persist(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    saved = save_ratings(
        run,
        {
            "candidates": {
                "01_anime__illustrated_scene:1": {
                    "overall": 4,
                    "identity": 5,
                    "commercial": 3,
                    "flags": ["boring_generic"],
                    "note": "ok",
                }
            },
            "director": {"overall": 4, "note": "varied"},
        },
    )
    loaded = load_ratings(run)
    assert loaded == saved
    assert loaded["candidates"]["01_anime__illustrated_scene:1"]["overall"] == 4
    (run / "recipes" / "01_anime__illustrated_scene").mkdir(parents=True)
    (run / "recipes" / "01_anime__illustrated_scene" / "quality.json").write_text(
        json.dumps({"candidates": [{"slot": 1, "hard_failed": True}]}),
        encoding="utf-8",
    )
    summary = recipe_summaries(tmp_path)
    assert summary
    row = next(item for item in summary if "anime" in item["recipe"])
    assert row["rated"] == 1
    assert row["hard_fail_rate"] == 1.0


def test_stub_cli_writes_run(tmp_path: Path) -> None:
    code = main(
        [
            "--case",
            "sweatshirt_01",
            "--mode",
            "fixed",
            "--candidates",
            "1",
            "--provider",
            "stub",
            "--runs-dir",
            str(tmp_path),
            "--label",
            "ci",
        ]
    )
    assert code == 0
    runs = list(tmp_path.iterdir())
    assert len(runs) == 1
    meta = json.loads((runs[0] / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["provider"] == "stub"
    assert meta["prompt_version"] == CREATIVE_PROMPT_VERSION
    assert (runs[0] / "reference_product.jpg").is_file()
    summary = json.loads(
        next((runs[0] / "recipes").glob("*/provider_request_summary.json")).read_text(
            encoding="utf-8"
        )
    )
    assert "api_key" not in json.dumps(summary)
    assert summary["seed_supported"] is False


def _tiny_ref() -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (320, 400), (20, 30, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()
