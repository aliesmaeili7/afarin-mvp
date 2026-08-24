"""Run fixed-recipe or Director creative evals into an immutable folder."""

from __future__ import annotations

import asyncio
import io
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

from app.providers.image.base import ImageProvider
from app.providers.image.creative_prompts import CREATIVE_PROMPT_VERSION
from app.providers.vision.base import CampaignDirection, PlannerContext, PlannerResult
from app.services.campaigns.creative_core import (
    RecipeSetResult,
    generate_recipe_set,
)
from app.services.campaigns.planner import planner_snapshot
from app.services.campaigns.recipes import recipe_from_direction, recipe_from_ids
from scripts.creative_eval.cases import FixtureError, resolve_image
from scripts.creative_eval.meta import reproducibility
from scripts.creative_eval.plan import EvalPlan
from scripts.creative_eval.ratings import empty_ratings
from scripts.creative_eval.sanitize import sanitize
from scripts.creative_eval.store import (
    allocate_run_dir,
    recipe_folder,
    write_json,
)


def prompt_campaign(case: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(visual_style=case.get("visual_style"))


def prompt_concept(direction: CampaignDirection | None) -> SimpleNamespace | None:
    if direction is None:
        return None
    return SimpleNamespace(
        visual_direction=direction.visual_direction,
        title_fa=direction.title_fa,
        headline_fa=direction.headline_fa,
        description_fa=direction.description_fa,
        background_prompt=direction.background_prompt,
    )


def planner_context(case: dict[str, Any], recipe: dict | None = None) -> PlannerContext:
    product = case.get("product") or {}
    return PlannerContext(
        product_name=str(product.get("name") or ""),
        description=product.get("description"),
        brand_name=case.get("brand_name"),
        price_text=product.get("price_text"),
        audience=case.get("audience"),
        objective=str(case.get("objective") or "sell_product"),
        visual_style=str(case.get("visual_style") or "modern"),
        recipe=recipe or {},
    )


def effective_brief(case: dict[str, Any]) -> dict[str, Any]:
    product = case.get("product") or {}
    return {
        "product_name": product.get("name"),
        "description": product.get("description"),
        "price_text": product.get("price_text"),
        "main_benefit": product.get("main_benefit"),
        "brand_name": case.get("brand_name"),
        "audience": case.get("audience"),
        "objective": case.get("objective"),
        "visual_style": case.get("visual_style"),
        "identity_constraints": list(case.get("identity_constraints") or []),
    }


def direction_dict(direction: CampaignDirection) -> dict[str, Any]:
    return {
        "title_fa": direction.title_fa,
        "description_fa": direction.description_fa,
        "angle": direction.angle,
        "headline_fa": direction.headline_fa,
        "visual_direction": direction.visual_direction,
        "style_id": direction.style_id,
        "template_id": direction.template_id,
        "identity_constraints": list(direction.identity_constraints),
        "warning_fa": direction.warning_fa,
        "image_direction": direction.image_direction,
        "background_prompt": direction.background_prompt,
        "text_safe_area": direction.text_safe_area,
    }


def director_output(result: PlannerResult) -> dict[str, Any]:
    snapshot = planner_snapshot(result)
    usage = result.usage
    snapshot["directions"] = [direction_dict(item) for item in result.directions]
    snapshot["usage"] = (
        None
        if usage is None
        else {
            "latency_ms": usage.latency_ms,
            "cost_usd": str(usage.cost_usd) if usage.cost_usd is not None else None,
            "model": usage.model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        }
    )
    return snapshot


def recipes_from_fixture(
    case: dict[str, Any], overrides: list[dict[str, str]]
) -> list[dict]:
    source = overrides or list(case.get("fixed_recipes") or [])
    if not source:
        raise FixtureError("fixed mode needs fixture.fixed_recipes or --recipes")
    constraints = list(case.get("identity_constraints") or [])
    built = []
    for item in source:
        built.append(
            recipe_from_ids(
                item["style_id"],
                item["template_id"],
                source="eval_fixed",
                identity_constraints=constraints or None,
            )
        )
    return built


def recipes_from_director(result: PlannerResult) -> list[dict]:
    snapshot = planner_snapshot(result)
    return [
        recipe_from_direction(item, planner=snapshot, source="eval_director")
        for item in result.directions
    ]


def _cost_of(frame) -> Decimal:
    if frame is None or not frame.cost_usd:
        return Decimal("0")
    return Decimal(frame.cost_usd)


def _llm_cost(payload: dict | None) -> Decimal:
    if not payload:
        return Decimal("0")
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict) or usage.get("cost_usd") is None:
        return Decimal("0")
    return Decimal(str(usage["cost_usd"]))


async def write_recipe_result(
    folder: Path,
    result: RecipeSetResult,
    *,
    case_id: str,
    run_id: str,
    timestamp: str,
    direction: dict | None = None,
    analysis: dict | None = None,
) -> dict[str, Any]:
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "recipe.json", result.recipe)
    (folder / "effective_prompt.txt").write_text(result.prompt + "\n", encoding="utf-8")
    write_json(
        folder / "prompt.json",
        {
            "prompt": result.prompt,
            "prompts": result.prompts,
            "prompt_version": result.prompt_version,
            "style_id": result.recipe.get("style_id"),
            "template_id": result.recipe.get("template_id"),
            "compatibility": result.compatibility or result.recipe.get("compatibility"),
        },
    )
    if result.architect is not None:
        write_json(folder / "architect.json", result.architect)
    if result.cleaned_jpeg is not None:
        (folder / "cleaned_reference.jpg").write_bytes(result.cleaned_jpeg)
    write_json(
        folder / "reference_analysis.json",
        analysis
        or (result.recipe.get("planner") or {}).get("reference_analysis")
        or {},
    )
    if result.candidate_request is not None:
        write_json(
            folder / "provider_request_summary.json",
            sanitize(result.candidate_request),
        )
    if direction is not None:
        write_json(folder / "direction.json", direction)
    if result.quality is not None:
        write_json(folder / "quality.json", result.quality)
    if result.llm_calls:
        write_json(folder / "llm_calls.json", sanitize(result.llm_calls))
    if result.image_requests:
        write_json(folder / "image_requests.json", sanitize(result.image_requests))

    metrics: dict[str, Any] = {
        "case_id": case_id,
        "run_id": run_id,
        "style_id": result.recipe.get("style_id"),
        "template_id": result.recipe.get("template_id"),
        "prompt_version": result.prompt_version,
        "auto_repair_used": result.auto_repair_used,
        "frames": [],
    }
    image_cost = Decimal("0")
    image_count = 0
    qc_calls = 1 if result.quality else 0
    if result.quality and result.repairs:
        qc_calls += 1

    for frame in result.candidates:
        dest = folder / f"candidate-{frame.slot}.jpg"
        dest.write_bytes(frame.jpeg)
        metrics["frames"].append(_frame_meta(frame, dest.name, timestamp))
        image_cost += _cost_of(frame)
        image_count += 1
    for frame in result.repairs:
        dest = folder / f"repair-{frame.slot}.jpg"
        dest.write_bytes(frame.jpeg)
        metrics["frames"].append(_frame_meta(frame, dest.name, timestamp))
        image_cost += _cost_of(frame)
        image_count += 1
    if result.story is not None:
        dest = folder / "story.jpg"
        dest.write_bytes(result.story.jpeg)
        metrics["frames"].append(_frame_meta(result.story, dest.name, timestamp))
        image_cost += _cost_of(result.story)
        image_count += 1
    if result.master is not None:
        dest = folder / "master-9x16.jpg"
        dest.write_bytes(result.master.jpeg)
        metrics["frames"].append(_frame_meta(result.master, dest.name, timestamp))
        image_cost += _cost_of(result.master)
        image_count += 1
    if result.master_crop_jpeg is not None:
        (folder / "crop-4x5.jpg").write_bytes(result.master_crop_jpeg)
    if result.error:
        write_json(folder / "error.json", {"error": result.error})
    write_json(folder / "metrics.json", metrics)
    return {
        "folder": folder.name,
        "style_id": result.recipe.get("style_id"),
        "template_id": result.recipe.get("template_id"),
        "candidates": len(result.candidates),
        "repairs": len(result.repairs),
        "story": result.story is not None,
        "master": result.master is not None,
        "error": result.error,
        "image_outputs": image_count,
        "image_cost_usd": str(image_cost) if image_count else None,
        "qc_calls": qc_calls,
        "qc_cost_usd": str(_llm_cost(result.quality)) if result.quality else None,
        "architect_calls": 1 if result.architect else 0,
        "architect_cost_usd": str(_llm_cost(result.architect)) if result.architect else None,
        "compatibility": result.compatibility or result.recipe.get("compatibility"),
    }


def _frame_meta(frame, filename: str, timestamp: str) -> dict[str, Any]:
    return {
        "file": filename,
        "slot": frame.slot,
        "kind": frame.kind,
        "role": frame.role,
        "provider": frame.provider,
        "model": frame.model,
        "width": frame.width,
        "height": frame.height,
        "latency_ms": frame.latency_ms,
        "cost_usd": frame.cost_usd,
        "prompt_version": CREATIVE_PROMPT_VERSION,
        "hard_failed": frame.hard_failed,
        "repaired": frame.repaired,
        "hidden": frame.hidden,
        "timestamp": frame.timestamp or timestamp,
        "quality": frame.quality,
    }


async def _one_recipe(
    *,
    recipe: dict,
    reference: bytes,
    original: bytes | None,
    analysis: dict,
    case: dict[str, Any],
    plan: EvalPlan,
    provider: ImageProvider,
    planner: Any,
    direction: CampaignDirection | None,
    timestamp: str,
    architect: Any | None = None,
) -> RecipeSetResult:
    concept = prompt_concept(direction)
    try:
        return await generate_recipe_set(
            recipe=recipe,
            reference=reference,
            original=original,
            analysis=analysis,
            campaign=prompt_campaign(case),
            concept=concept,
            planner_context=planner_context(case, recipe),
            provider=provider,
            planner=planner,
            architect=architect,
            n=plan.candidates,
            variation=0,
            quality_check=plan.quality_check,
            repair=plan.repair,  # type: ignore[arg-type]
            story=plan.story,
            master_crop=plan.master_crop,
            timestamp=timestamp,
        )
    except Exception as error:
        failed = RecipeSetResult(
            recipe=recipe,
            prompt="",
            prompt_version=CREATIVE_PROMPT_VERSION,
            error=str(error),
        )
        return failed


async def execute_run(
    *,
    case: dict[str, Any],
    plan: EvalPlan,
    provider: ImageProvider,
    planner: Any,
    recipes: list[dict],
    directions: list[CampaignDirection] | None,
    director: PlannerResult | None,
    runs_dir: Path,
    dry_run: bool = False,
    architect: Any | None = None,
) -> Path:
    if dry_run:
        raise RuntimeError("execute_run must not be called for --dry-run")

    image_path = resolve_image(case, require=True)
    reference = _reference_jpeg(image_path)
    original = image_path.read_bytes()
    analysis = {}
    if director is not None:
        analysis = director.reference_analysis.as_dict()
    timestamp = datetime.now(UTC).isoformat()
    run_dir = allocate_run_dir(
        case_id=plan.case_id, label=plan.label, runs_dir=runs_dir
    )
    run_id = run_dir.name

    fixture_copy = {
        key: value
        for key, value in case.items()
        if not str(key).startswith("_")
    }
    write_json(run_dir / "input_fixture.json", fixture_copy)
    write_json(run_dir / "effective_brief.json", effective_brief(case))
    (run_dir / "reference_product.jpg").write_bytes(reference)
    write_json(run_dir / "reference_analysis.json", analysis)
    write_json(run_dir / "ratings.json", empty_ratings())
    if director is not None:
        write_json(run_dir / "director_output.json", director_output(director))
        if director.llm_trace is not None:
            write_json(
                run_dir / "llm_calls.json",
                sanitize([director.llm_trace.as_dict()]),
            )

    semaphore = asyncio.Semaphore(max(1, min(3, plan.concurrency)))
    summaries: list[dict[str, Any]] = []

    async def work(index: int, recipe: dict) -> dict[str, Any]:
        direction = None
        if directions is not None and index < len(directions):
            direction = directions[index]
        async with semaphore:
            result = await _one_recipe(
                recipe=recipe,
                reference=reference,
                original=original,
                analysis=analysis,
                case=case,
                plan=plan,
                provider=provider,
                planner=planner,
                architect=architect,
                direction=direction,
                timestamp=timestamp,
            )
        folder = run_dir / "recipes" / recipe_folder(
            index + 1,
            str(recipe.get("style_id")),
            str(recipe.get("template_id")),
        )
        return await write_recipe_result(
            folder,
            result,
            case_id=plan.case_id,
            run_id=run_id,
            timestamp=timestamp,
            direction=direction_dict(direction) if direction else None,
            analysis=analysis,
        )

    if plan.candidates > 0 and recipes:
        summaries = list(
            await asyncio.gather(
                *(work(index, recipe) for index, recipe in enumerate(recipes))
            )
        )
    elif recipes:
        for index, recipe in enumerate(recipes):
            folder = run_dir / "recipes" / recipe_folder(
                index + 1,
                str(recipe.get("style_id")),
                str(recipe.get("template_id")),
            )
            empty = RecipeSetResult(
                recipe=recipe,
                prompt="",
                prompt_version=CREATIVE_PROMPT_VERSION,
            )
            direction = (
                directions[index]
                if directions is not None and index < len(directions)
                else None
            )
            summaries.append(
                await write_recipe_result(
                    folder,
                    empty,
                    case_id=plan.case_id,
                    run_id=run_id,
                    timestamp=timestamp,
                    direction=direction_dict(direction) if direction else None,
                    analysis=analysis,
                )
            )

    director_cost = _llm_cost(director_output(director) if director else None)
    qc_cost = Decimal("0")
    architect_cost = Decimal("0")
    image_cost = Decimal("0")
    image_outputs = 0
    qc_calls = 0
    architect_calls = 0
    for row in summaries:
        image_outputs += int(row.get("image_outputs") or 0)
        if row.get("image_cost_usd"):
            image_cost += Decimal(str(row["image_cost_usd"]))
        qc_calls += int(row.get("qc_calls") or 0)
        if row.get("qc_cost_usd"):
            qc_cost += Decimal(str(row["qc_cost_usd"]))
        architect_calls += int(row.get("architect_calls") or 0)
        if row.get("architect_cost_usd"):
            architect_cost += Decimal(str(row["architect_cost_usd"]))

    cleaned = next(run_dir.glob("recipes/*/cleaned_reference.jpg"), None)
    if cleaned is not None and not (run_dir / "cleaned_reference.jpg").exists():
        (run_dir / "cleaned_reference.jpg").write_bytes(cleaned.read_bytes())

    write_json(
        run_dir / "cost.json",
        {
            "llm_calls": {
                "director": 1 if director is not None else 0,
                "architect": architect_calls,
                "qc": qc_calls,
            },
            "image_outputs": {
                "candidates": sum(int(row.get("candidates") or 0) for row in summaries),
                "repairs": sum(int(row.get("repairs") or 0) for row in summaries),
                "story": sum(1 for row in summaries if row.get("story")),
                "master": sum(1 for row in summaries if row.get("master")),
                "total": image_outputs,
            },
            "cost_usd": {
                "director_llm": str(director_cost) if director is not None else None,
                "architect_llm": str(architect_cost) if architect_calls else None,
                "qc_llm": str(qc_cost) if qc_calls else None,
                "images": str(image_cost) if image_outputs else None,
                "total": str(director_cost + architect_cost + qc_cost + image_cost),
            },
        },
    )
    write_json(
        run_dir / "run_meta.json",
        {
            "run_id": run_id,
            "case_id": plan.case_id,
            "mode": plan.mode,
            "label": plan.label,
            "prompt_version": CREATIVE_PROMPT_VERSION,
            "provider": plan.provider,
            "image_model": provider.model,
            "planner_model": getattr(planner, "model", None),
            "architect_model": getattr(architect, "model", None) if architect else None,
            "director_model": getattr(planner, "model", None),
            "qc_model": getattr(planner, "model", None),
            "candidates": plan.candidates,
            "quality_check": plan.quality_check,
            "repair": plan.repair,
            "story": plan.story,
            "master_crop": plan.master_crop,
            "paid": plan.paid,
            "experiment_id": plan.experiment_id,
            "category": case.get("category"),
            "created_at": timestamp,
            "recipes": summaries,
            **reproducibility(case=case, provider=provider, planner=planner),
        },
    )
    return run_dir


def _reference_jpeg(path: Path) -> bytes:
    image = Image.open(path).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()
