"""
Educational Agent contract: one call, one prompt, one image, one retry.

These talk to the core service directly with fake agents, so they can count
calls and assert what the image provider actually received.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.providers.education import set_educational_agent
from app.providers.education.base import EducationalAgentContext, EducationalPostResult
from app.providers.education.openrouter import result_from
from app.providers.education.prompts import (
    FINAL_PROMPT_MAX_CHARS,
    educational_agent_system,
    educational_user_prompt,
)
from app.providers.education.schemas import LlmEducationalPostResult
from app.providers.education.stub import stub_educational_result
from app.providers.education.validate import validate_educational_result
from app.providers.image import set_image_provider
from app.providers.image.base import ImageRequest, ImageResult, ImageUsage
from app.providers.llm.base import LlmUsage
from app.services.education import core

FA_PROMPT = "برای کلاس ششم یک پست درباره اعداد اعشاری بساز. عنوان: ممیز کوچولو"
EN_PROMPT = "Make a post about the water cycle for grade 4. Title: Water Cycle"


class CountingAgent:
    """Records every call so we can prove there is exactly one."""

    name = "counting"
    model = "counting-model"

    def __init__(self, result: EducationalPostResult) -> None:
        self._result = result
        self.calls: list[dict] = []

    async def create_post(self, context, *, correction=None):
        self.calls.append({"context": context, "correction": correction})
        return self._result


class SequenceAgent:
    """Returns a scripted list of results, one per call."""

    name = "sequence"
    model = "sequence-model"

    def __init__(self, *results: EducationalPostResult) -> None:
        self._results = list(results)
        self.calls: list[str | None] = []

    async def create_post(self, context, *, correction=None):
        self.calls.append(correction)
        index = min(len(self.calls) - 1, len(self._results) - 1)
        return self._results[index]


class RecordingImageProvider:
    name = "recording"
    model = "recording-model"

    def __init__(self) -> None:
        self.requests: list[ImageRequest] = []

    async def generate(self, request: ImageRequest) -> ImageResult:
        self.requests.append(request)
        return ImageResult(
            content=b"jpeg-bytes",
            contents=(b"jpeg-bytes",),
            media_type="image/jpeg",
            usage=ImageUsage(
                latency_ms=5, cost_usd=Decimal("0.01"), model=self.model
            ),
        )


@pytest.fixture(autouse=True)
def _reset_providers():
    yield
    set_educational_agent(None)
    set_image_provider(None)


def _valid(prompt: str = FA_PROMPT) -> EducationalPostResult:
    return stub_educational_result(EducationalAgentContext(user_prompt=prompt))


async def test_one_llm_call_produces_theme_and_final_prompt() -> None:
    agent = CountingAgent(_valid())
    planned = await core.plan_validated_post(user_prompt=FA_PROMPT, agent=agent)

    assert len(agent.calls) == 1
    assert agent.calls[0]["correction"] is None
    result = planned.result
    assert result.theme.name_suggestion
    assert result.theme.mood
    assert result.theme.lighting
    assert result.final_prompt
    assert planned.retry_used is False
    dumped = result.as_dict()
    assert "content" not in dumped
    assert "visual_plan" not in dumped
    assert "overlay_items" not in dumped


async def test_the_agent_receives_the_raw_prompt_and_no_extra_fields() -> None:
    agent = CountingAgent(_valid())
    await core.plan_validated_post(user_prompt=FA_PROMPT, agent=agent)

    context = agent.calls[0]["context"]
    assert context.user_prompt == FA_PROMPT
    assert context.selected_theme is None
    assert context.aspect == "1:1"
    for absent in (
        "grade",
        "subject",
        "tone",
        "audience",
        "title",
        "visual_style",
        "font_ids",
    ):
        assert not hasattr(context, absent)


async def test_final_prompt_reaches_the_image_provider_unchanged() -> None:
    provider = RecordingImageProvider()
    set_image_provider(provider)
    result = _valid()

    generated = await core.generate_post_image(result.final_prompt)

    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert request.prompt == result.final_prompt
    assert request.aspect_ratio == "1:1"
    assert request.n == 1
    assert request.references == ()
    # Educational generation names GPT Image 2; advertising ImageRequests do not.
    assert request.model == "openai/gpt-image-2"
    assert generated.content == b"jpeg-bytes"


def test_advertising_and_educational_image_models_stay_apart() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["image_model"].default == "bytedance-seed/seedream-4.5"
    assert (
        Settings.model_fields["educational_image_model"].default == "openai/gpt-image-2"
    )


async def test_exactly_one_image_is_requested_even_when_more_come_back() -> None:
    class ChattyProvider(RecordingImageProvider):
        async def generate(self, request):
            await super().generate(request)
            return ImageResult(
                content=b"one",
                contents=(b"one", b"two", b"three"),
                media_type="image/jpeg",
                usage=ImageUsage(latency_ms=1),
            )

    provider = ChattyProvider()
    set_image_provider(provider)
    generated = await core.generate_post_image("a square 1:1 illustration")

    assert provider.requests[0].n == 1
    assert generated.content == b"one"


async def test_persian_prompt_yields_persian_image_prompt() -> None:
    result = _valid(FA_PROMPT)
    assert result.language == "fa"
    assert any("\u0600" <= ch <= "\u06ff" for ch in result.final_prompt)
    assert "ممیز کوچولو" in result.final_prompt
    assert validate_educational_result(result).ok


async def test_english_prompt_yields_english_image_prompt() -> None:
    result = _valid(EN_PROMPT)
    assert result.language == "en"
    assert not any("\u0600" <= ch <= "\u06ff" for ch in result.final_prompt)
    assert "Water Cycle" in result.final_prompt
    assert validate_educational_result(result).ok


async def test_a_selected_theme_is_passed_to_the_agent() -> None:
    agent = CountingAgent(_valid())
    theme = {
        "palette": {"primary": ["#123456"]},
        "name": "تم من",
        "mood": "calm",
        "illustration_style": "watercolor",
    }
    await core.plan_validated_post(
        user_prompt=FA_PROMPT, selected_theme=theme, agent=agent
    )
    assert agent.calls[0]["context"].selected_theme == theme


async def test_one_semantic_retry_repairs_an_invalid_response() -> None:
    broken = replace(_valid(), final_prompt="x" * (FINAL_PROMPT_MAX_CHARS + 50))
    agent = SequenceAgent(broken, _valid())

    planned = await core.plan_validated_post(user_prompt=FA_PROMPT, agent=agent)

    assert len(agent.calls) == 2
    assert agent.calls[0] is None
    assert "failed validation" in (agent.calls[1] or "")
    assert planned.retry_used is True
    assert planned.validation.ok


async def test_a_second_invalid_response_fails_with_zero_image_calls() -> None:
    broken = replace(_valid(), final_prompt="{not a prompt at all}")
    agent = SequenceAgent(broken, broken)
    provider = RecordingImageProvider()
    set_image_provider(provider)

    with pytest.raises(ApiError):
        await core.plan_validated_post(user_prompt=FA_PROMPT, agent=agent)

    assert len(agent.calls) == 2
    assert provider.requests == []


async def test_a_valid_prompt_is_never_rewritten() -> None:
    original = _valid()
    agent = CountingAgent(original)
    planned = await core.plan_validated_post(user_prompt=FA_PROMPT, agent=agent)
    assert planned.result.final_prompt == original.final_prompt


def test_validation_rejects_an_over_long_prompt() -> None:
    result = replace(_valid(), final_prompt="ت" * (FINAL_PROMPT_MAX_CHARS + 1))
    validation = validate_educational_result(result)
    assert not validation.ok
    assert any("final_prompt exceeds" in error for error in validation.errors)


def test_validation_rejects_a_json_dump_as_a_prompt() -> None:
    result = replace(_valid(), final_prompt='{"scene": "a square 1:1 room"}')
    validation = validate_educational_result(result)
    assert not validation.ok
    assert any("JSON" in error for error in validation.errors)


def test_validation_requires_the_square_format() -> None:
    result = replace(_valid(EN_PROMPT), final_prompt="A tall vertical illustration.")
    validation = validate_educational_result(result)
    assert not validation.ok
    assert any("square" in error for error in validation.errors)


def test_validation_rejects_a_language_mismatch() -> None:
    persian = _valid(FA_PROMPT)
    claimed_english = replace(persian, language="en")
    validation = validate_educational_result(claimed_english)
    assert not validation.ok
    assert any("English only" in error for error in validation.errors)


def test_validation_rejects_an_overlay_pipeline_prompt() -> None:
    result = replace(
        _valid(EN_PROMPT),
        final_prompt=(
            "Create a square 1:1 illustration. Leave a clean empty band for "
            "the title. Do not draw the title wording."
        ),
    )
    validation = validate_educational_result(result)
    assert not validation.ok
    assert any("overlay" in error for error in validation.errors)


def test_a_selected_theme_makes_the_agents_theme_block_advisory() -> None:
    """
    A user-selected theme wins, so a weak theme block from the agent must not
    fail the whole call and waste it.
    """
    result = _valid()
    theme = replace(result.theme, primary_colors=("not-a-hex",))
    broken = replace(result, theme=theme)

    assert not validate_educational_result(broken, theme_was_selected=False).ok
    assert validate_educational_result(broken, theme_was_selected=True).ok


def test_the_system_prompt_asks_for_a_finished_image_not_overlays() -> None:
    system = educational_agent_system()
    lowered = system.lower()
    assert str(FINAL_PROMPT_MAX_CHARS) in system
    assert "overlay" in lowered
    assert "cta" in lowered
    assert "final_prompt" in lowered
    assert "not overlay text" in lowered or "will not overlay" in lowered
    assert "style memory" in lowered or "look" in lowered


def test_the_user_prompt_carries_the_request_and_the_theme() -> None:
    theme = {"name": "تم من", "palette": {"primary": ["#123456"]}}
    text = educational_user_prompt(
        EducationalAgentContext(user_prompt=FA_PROMPT, selected_theme=theme)
    )
    assert FA_PROMPT in text
    assert "#123456" in text
    assert "1:1" in text
    assert "CTA" in text or "cta" in text.lower()

    without = educational_user_prompt(
        EducationalAgentContext(user_prompt=FA_PROMPT)
    )
    assert "No theme was selected" in without


def test_schema_output_maps_onto_the_domain_result() -> None:
    """A round trip through the strict schema keeps every field."""
    payload = LlmEducationalPostResult.model_validate(
        {
            "language": "fa",
            "final_prompt": (
                "یک پوستر آموزشی مربعی 1:1 با مسیر رنگی بساز. "
                "عنوان ممیز کوچولو را در تصویر بنویس."
            ),
            "theme": {
                "name_suggestion": "ریاضی بنفش",
                "primary_colors": ["#7c3aed"],
                "secondary_colors": ["#fde047"],
                "illustration_style": "خمیری",
                "mood": "بازیگوش",
                "lighting": "نور نرم",
                "shape_language": "گرد",
                "decorative_motifs": ["ستاره"],
            },
            "theme_style_notes": "خمیری بنفش",
            "safety_notes": None,
        }
    )
    result = result_from(payload, usage=LlmUsage(latency_ms=42))

    assert result.language == "fa"
    assert "ممیز کوچولو" in result.final_prompt
    assert result.theme.mood == "بازیگوش"
    assert result.theme.lighting == "نور نرم"
    assert result.usage is not None and result.usage.latency_ms == 42
    assert validate_educational_result(result).ok
    dumped = result.as_dict()
    assert dumped["theme"]["illustration_style"] == "خمیری"
    assert "content" not in dumped
    assert "font_role" not in dumped["theme"]
