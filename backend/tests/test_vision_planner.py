"""Visual planner client: model fallback and OpenAI-strict schema."""

from app.core.config import Settings
from app.providers.vision.base import PlannerContext
from app.providers.vision.openrouter import OpenRouterVisualPlanner
from tests.conftest import png_bytes
from tests.fakes import FakeLlmClient


def _ctx() -> PlannerContext:
    return PlannerContext(
        product_name="هودی",
        description=None,
        brand_name=None,
        price_text=None,
        audience=None,
        objective="promotion",
        visual_style="friendly",
        concept_title_fa="ساده",
        concept_headline_fa="گرم بپوش",
        concept_visual_direction="studio",
    )


def _recipes() -> dict:
    base = {
        "style_id": "photoreal_commercial",
        "template_id": "hero_product",
        "title_fa": "واقعی و واضح",
        "description_fa": "محصول در مرکز",
        "scene_direction": "clean studio hero",
        "text_safe_area": "bottom",
        "identity_constraints": ["keep colors"],
        "warning_fa": "",
    }
    return {
        "product_type": "hoodie",
        "visual_identity": ["navy fabric"],
        "identity_constraints": ["keep silhouette"],
        "unsuitable_style_ids": [],
        "unsuitable_template_ids": [],
        "input_quality": {"status": "ok", "reasons": []},
        "recommended_recipes": [
            base,
            {
                **base,
                "style_id": "anime",
                "template_id": "illustrated_scene",
                "title_fa": "تصویرسازی",
            },
            {
                **base,
                "style_id": "surreal",
                "template_id": "giant_miniature_world",
                "title_fa": "ایده غیرمنتظره",
            },
        ],
        "forbidden_claims": [],
    }


async def test_empty_visual_planner_model_uses_llm_model() -> None:
    llm = FakeLlmClient([_recipes()])
    planner = OpenRouterVisualPlanner(
        llm,
        Settings(
            visual_planner_model="  ",
            llm_model="openai/fallback-llm",
            openrouter_api_key="sk-test",
            content_provider="openrouter",
        ),
    )
    result = await planner.plan_recipes(png_bytes(64, 80), _ctx())
    assert result.input_quality.ok
    assert llm.calls[0]["model"] == "openai/fallback-llm"
    assert len(result.recommended_recipes) == 3
