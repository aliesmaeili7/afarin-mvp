"""Visual planner / Creative Director client: model fallback and schema."""

from app.core.config import Settings
from app.providers.vision.base import PlannerContext
from app.providers.vision.openrouter import OpenRouterVisualPlanner
from tests.conftest import png_bytes
from tests.fakes import FakeLlmClient, three_directions


def _ctx() -> PlannerContext:
    return PlannerContext(
        product_name="هودی",
        description=None,
        brand_name=None,
        price_text=None,
        audience=None,
        objective="promotion",
        visual_style="friendly",
    )


async def test_empty_visual_planner_model_uses_llm_model() -> None:
    llm = FakeLlmClient([three_directions()])
    planner = OpenRouterVisualPlanner(
        llm,
        Settings(
            visual_planner_model="  ",
            llm_model="openai/fallback-llm",
            openrouter_api_key="sk-test",
            content_provider="openrouter",
        ),
    )
    result = await planner.plan_directions(png_bytes(64, 80), _ctx())
    assert result.input_quality.ok
    assert llm.calls[0]["model"] == "openai/fallback-llm"
    assert len(result.directions) == 3
    assert result.directions[0].style_id == "photoreal_commercial"
    assert llm.calls[0]["schema_name"] == "creative_director"
    assert result.llm_trace is not None
    assert result.llm_trace.name == "creative_director"
    assert result.llm_trace.user
    assert result.llm_trace.output
    assert "data:image" not in result.llm_trace.output


async def test_check_input_quality_does_not_call_the_planner() -> None:
    llm = FakeLlmClient([three_directions()])
    planner = OpenRouterVisualPlanner(
        llm,
        Settings(
            visual_planner_model="openai/planner",
            openrouter_api_key="sk-test",
            content_provider="openrouter",
        ),
    )
    quality = await planner.check_input_quality(png_bytes(320, 400), _ctx())
    assert quality.ok
    assert llm.calls == []


async def test_invalid_catalog_ids_fall_back() -> None:
    payload = three_directions()
    payload["directions"][0]["style_id"] = "not-a-style"
    payload["directions"][0]["template_id"] = "not-a-template"
    llm = FakeLlmClient([payload])
    planner = OpenRouterVisualPlanner(
        llm,
        Settings(openrouter_api_key="sk-test", content_provider="openrouter"),
    )
    result = await planner.plan_directions(png_bytes(64, 80), _ctx())
    assert result.directions[0].style_id == "photoreal_commercial"
    assert result.directions[0].template_id == "hero_product"
