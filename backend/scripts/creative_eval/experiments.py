"""Load and validate batch experiment manifests."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.creative_eval.cases import FixtureError, parse_recipes
from scripts.creative_eval.plan import EvalPlan, build_plan

EVAL_ROOT = Path(__file__).resolve().parents[2] / "eval"
EXPERIMENTS_DIR = EVAL_ROOT / "experiments"

MODES = frozenset({"fixed", "director"})


def load_experiment(
    experiment_id: str, *, experiments_dir: Path | None = None
) -> dict[str, Any]:
    folder = experiments_dir or EXPERIMENTS_DIR
    path = folder / f"{experiment_id}.json"
    if not path.is_file():
        names = ", ".join(p.stem for p in sorted(folder.glob("*.json"))) or "(none)"
        raise FixtureError(f"unknown experiment {experiment_id!r}; available: {names}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FixtureError(f"{path}: invalid JSON ({error})") from error
    if not isinstance(data, dict):
        raise FixtureError(f"{path}: experiment must be a JSON object")
    return validate_experiment(data, path=path)


def validate_experiment(data: dict[str, Any], *, path: Path) -> dict[str, Any]:
    experiment_id = data.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise FixtureError(f"{path}: experiment_id is required")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise FixtureError(f"{path}: cases must be a non-empty list")
    repair = data.get("repair", "none")
    if repair not in ("none", "production"):
        raise FixtureError(f"{path}: repair must be none or production")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(cases):
        if not isinstance(item, dict):
            raise FixtureError(f"{path}: cases[{index}] must be an object")
        case_id = item.get("case")
        if not isinstance(case_id, str) or not case_id.strip():
            raise FixtureError(f"{path}: cases[{index}].case is required")
        mode = item.get("mode")
        if mode not in MODES:
            raise FixtureError(f"{path}: cases[{index}].mode must be fixed or director")
        candidates = item.get("candidates", data.get("candidates", 1))
        if candidates not in (0, 1, 3):
            raise FixtureError(f"{path}: cases[{index}].candidates must be 0, 1, or 3")
        recipes_raw = item.get("recipes") or []
        recipes: list[dict[str, str]] = []
        if recipes_raw:
            if not isinstance(recipes_raw, list):
                raise FixtureError(f"{path}: cases[{index}].recipes must be a list")
            recipes = parse_recipes(",".join(str(row) for row in recipes_raw))
        if mode == "fixed" and not recipes:
            # Allowed: fixture.fixed_recipes used later.
            recipes = []
        if mode == "director" and recipes:
            raise FixtureError(
                f"{path}: cases[{index}] director mode cannot set recipes"
            )
        normalized.append(
            {
                "case": case_id,
                "mode": mode,
                "recipes": recipes,
                "candidates": candidates,
                "quality_check": bool(
                    item.get("quality_check", data.get("quality_check", False))
                ),
                "repair": str(item.get("repair", repair)),
                "story": bool(item.get("story", data.get("story", False))),
                "master_crop": bool(
                    item.get("master_crop", data.get("master_crop", False))
                ),
            }
        )
    out = dict(data)
    out["_path"] = str(path)
    out["cases"] = normalized
    out["repair"] = repair
    return out


def plans_for_experiment(
    experiment: dict[str, Any],
    *,
    provider: str,
    paid: bool,
    label: str | None,
    concurrency: int,
) -> list[EvalPlan]:
    plans: list[EvalPlan] = []
    for item in experiment["cases"]:
        recipes = item["recipes"] or (
            [{"style_id": "(director)", "template_id": "(director)"}] * 3
            if item["mode"] == "director"
            else [{"style_id": "(fixture)", "template_id": "(fixture)"}]
        )
        plans.append(
            build_plan(
                case_id=item["case"],
                mode=item["mode"],
                recipes=recipes,
                candidates=item["candidates"],
                quality_check=item["quality_check"],
                repair=item["repair"],
                story=item["story"],
                master_crop=item["master_crop"],
                provider=provider,
                paid=paid,
                label=label or experiment.get("experiment_id"),
                concurrency=concurrency,
                experiment_id=experiment.get("experiment_id"),
            )
        )
    return plans


def render_batch_plan(experiment_id: str, plans: list[EvalPlan]) -> str:
    director = sum(plan.director_llm_calls for plan in plans)
    architect = sum(plan.architect_llm_calls for plan in plans)
    qc = sum(plan.qc_llm_calls for plan in plans)
    images = sum(plan.image_outputs for plan in plans)
    repairs = sum(plan.image_repairs_max for plan in plans)
    cost = sum((plan.estimated_image_usd for plan in plans), Decimal("0"))
    lines = [
        f"Creative eval batch: {experiment_id}",
        "  TOTAL:",
        f"    cases:         {len(plans)}",
        f"    recipes:       {sum(len(plan.recipes) for plan in plans)}",
        f"    LLM calls:     {director + architect + qc} "
        f"(Director {director}, Architect {architect}, QC {qc})",
        f"    paid image outputs: {images} (+{repairs} repair max)",
        f"    estimated cost: ${cost}",
        "  jobs:",
    ]
    for plan in plans:
        recipe_txt = ", ".join(
            f"{item['style_id']}:{item['template_id']}" for item in plan.recipes
        )
        lines.append(
            f"    - {plan.case_id} {plan.mode} candidates={plan.candidates} "
            f"qc={plan.quality_check} [{recipe_txt}]"
        )
    return "\n".join(lines)
