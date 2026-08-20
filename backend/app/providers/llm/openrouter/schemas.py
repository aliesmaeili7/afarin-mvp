from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.content.copy import CaptionSet, ReelConcept


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmConcept(_Strict):
    title_fa: str = Field(min_length=1, max_length=80)
    headline_fa: str = Field(min_length=1, max_length=80)
    description_fa: str = Field(min_length=1, max_length=400)
    visual_direction: str = Field(min_length=1, max_length=240)
    background_prompt: str = Field(min_length=1, max_length=400)


class LlmConcepts(_Strict):
    concepts: list[LlmConcept] = Field(min_length=3, max_length=3)


class LlmReel(_Strict):
    hook_fa: str = Field(min_length=1, max_length=160)
    scenes_fa: list[str] = Field(min_length=3, max_length=3)
    cta_fa: str = Field(min_length=1, max_length=80)
    voiceover_fa: str = Field(min_length=1, max_length=400)
    duration_seconds: int = Field(ge=10, le=15)


class LlmCopyPackage(_Strict):
    caption_short: str = Field(min_length=1, max_length=900)
    caption_friendly: str = Field(min_length=1, max_length=900)
    caption_persuasive: str = Field(min_length=1, max_length=900)
    story_ideas: list[str] = Field(min_length=3, max_length=3)
    cta_fa: str = Field(min_length=1, max_length=80)
    hashtags: str = Field(min_length=1, max_length=400)
    subheadline_fa: str = Field(min_length=1, max_length=120)
    reel: LlmReel


class LlmRewrite(_Strict):
    text_fa: str = Field(min_length=1, max_length=900)


def captions_from(package: LlmCopyPackage) -> CaptionSet:
    return CaptionSet(
        caption_short=package.caption_short,
        caption_friendly=package.caption_friendly,
        caption_persuasive=package.caption_persuasive,
    )


def reel_from(package: LlmCopyPackage) -> ReelConcept:
    reel = package.reel
    return ReelConcept(
        hook_fa=reel.hook_fa,
        scenes_fa=list(reel.scenes_fa),
        cta_fa=reel.cta_fa,
        voiceover_fa=reel.voiceover_fa,
        duration_seconds=reel.duration_seconds,
    )


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema that OpenRouter's strict mode will accept."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", None) or schema.pop("definitions", None)
    if defs:
        schema = _inline_refs(schema, defs)
    return _require_closed_objects(schema)


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            name = node["$ref"].rsplit("/", 1)[-1]
            if name in defs:
                return _inline_refs(defs[name], defs)
        return {key: _inline_refs(value, defs) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _require_closed_objects(node: Any) -> Any:
    if isinstance(node, dict):
        cleaned = {
            key: _require_closed_objects(value)
            for key, value in node.items()
            if key != "default"
        }
        if cleaned.get("type") == "object":
            cleaned["additionalProperties"] = False
            cleaned.setdefault("properties", {})
            # OpenAI/OpenRouter strict mode rejects defaults and requires every
            # property listed. Pydantic omits fields with defaults from
            # `required`, which 400s the visual planner.
            cleaned["required"] = list(cleaned["properties"].keys())
        return cleaned
    if isinstance(node, list):
        return [_require_closed_objects(item) for item in node]
    return node
