"""CLI for the internal creative evaluation lab."""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
import webbrowser
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

from scripts.creative_eval.cases import (
    CASES_DIR,
    RUNS_DIR,
    FixtureError,
    catalog_recipes,
    load_case,
    parse_recipes,
    resolve_image,
)
from scripts.creative_eval.experiments import (
    EXPERIMENTS_DIR,
    load_experiment,
    render_batch_plan,
)
from scripts.creative_eval.plan import EvalPlan, build_plan, render_plan
from scripts.creative_eval.runner import (
    execute_run,
    planner_context,
    recipes_from_director,
    recipes_from_fixture,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Internal creative eval. Never called from campaign requests. "
            "Paid OpenRouter runs require --provider openrouter --paid."
        )
    )
    parser.add_argument(
        "--experiment",
        default="",
        help="batch experiment_id from eval/experiments/*.json",
    )
    parser.add_argument("--case", default="", help="fixture case_id")
    parser.add_argument("--mode", default="", choices=("", "fixed", "director"))
    parser.add_argument(
        "--recipes",
        default="",
        help="comma-separated style_id:template_id (fixed mode)",
    )
    parser.add_argument("--all-styles", action="store_true")
    parser.add_argument("--all-templates", action="store_true")
    parser.add_argument("--style", default="", help="fixed style for --all-templates")
    parser.add_argument(
        "--template", default="", help="fixed template for --all-styles"
    )
    parser.add_argument("--candidates", type=int, default=1, choices=(0, 1, 3))
    parser.add_argument("--story", action="store_true")
    parser.add_argument("--quality-check", action="store_true")
    parser.add_argument(
        "--repair",
        choices=("none", "production"),
        default="none",
    )
    parser.add_argument("--master-crop", action="store_true")
    parser.add_argument("--provider", choices=("stub", "openrouter"), default="stub")
    parser.add_argument(
        "--paid",
        action="store_true",
        help="required for --provider openrouter; makes real paid calls",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and make ZERO provider calls",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="required for catalog sweeps and paid experiment batches",
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--label", default="", help="prompt experiment label")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--cases-dir", type=Path, default=None)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--experiments-dir", type=Path, default=None)
    return parser


def _providers(name: str) -> tuple[Any, Any, Any]:
    if name == "stub":
        from app.providers.image.stub import StubImageProvider
        from app.providers.vision.stub import StubPromptArchitect, StubVisualPlanner

        return StubImageProvider(), StubVisualPlanner(), StubPromptArchitect()
    from app.core.config import get_settings
    from app.providers.image.openrouter.client import OpenRouterImageClient
    from app.providers.image.openrouter.provider import OpenRouterImageProvider
    from app.providers.llm.openrouter.client import OpenRouterClient
    from app.providers.vision.openrouter import (
        OpenRouterPromptArchitect,
        OpenRouterVisualPlanner,
    )

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required for --provider openrouter")
    llm = OpenRouterClient(settings)
    image = OpenRouterImageProvider(OpenRouterImageClient(settings), settings)
    planner = OpenRouterVisualPlanner(llm, settings)
    architect = OpenRouterPromptArchitect(llm, settings)
    return image, planner, architect


def _recipes_for_mode(args: argparse.Namespace, case: dict) -> list[dict[str, str]]:
    if args.mode == "director":
        if args.recipes or args.all_styles or args.all_templates:
            raise FixtureError("director mode ignores recipe overrides; omit them")
        return []
    sweep = catalog_recipes(
        all_styles=args.all_styles,
        all_templates=args.all_templates,
        style_id=args.style or None,
        template_id=args.template or None,
    )
    if sweep:
        return sweep
    if args.recipes:
        return parse_recipes(args.recipes)
    return list(case.get("fixed_recipes") or [])


def _refuse_paid(message: str) -> int:
    print(f"\n{message}", file=sys.stderr)
    return 2


def _paid_gates(
    *,
    provider: str,
    paid: bool,
    dry_run: bool,
    confirm: bool,
    sweep: bool,
    experiment: bool,
    image_outputs: int,
    estimated_usd: Any,
    recipe_count: int,
) -> int | None:
    if dry_run:
        return None
    if provider == "openrouter" and not paid:
        return _refuse_paid(
            "Refusing paid generation. Pass --provider openrouter --paid "
            "to spend image/LLM budget, or --provider stub / --dry-run."
        )
    if provider == "openrouter" and sweep and not confirm:
        return _refuse_paid(
            "Refusing catalog sweep without --confirm. "
            f"{recipe_count} recipes, "
            f"~{image_outputs} image outputs, "
            f"~${estimated_usd}."
        )
    if provider == "openrouter" and experiment and not confirm:
        return _refuse_paid(
            "Refusing paid experiment batch without --confirm. "
            f"~{image_outputs} image outputs, ~${estimated_usd}."
        )
    return None


async def _run_one(
    *,
    case: dict[str, Any],
    plan: EvalPlan,
    recipe_refs: list[dict[str, str]],
    provider: Any,
    planner: Any,
    architect: Any,
    runs_dir: Path,
) -> Path:
    director_result = None
    recipes: list[dict] = []
    directions = None
    if plan.mode == "director":
        image_bytes = resolve_image(case, require=True).read_bytes()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        director_result = await planner.plan_directions(
            buffer.getvalue(), planner_context(case)
        )
        recipes = recipes_from_director(director_result)
        directions = list(director_result.directions)
    else:
        recipes = recipes_from_fixture(case, recipe_refs)
        directions = None
    return await execute_run(
        case=case,
        plan=plan,
        provider=provider,
        planner=planner,
        architect=architect,
        recipes=recipes,
        directions=directions,
        director=director_result,
        runs_dir=runs_dir,
    )


def _print_review(run_dir: Path, open_browser: bool) -> None:
    print(f"\nwrote {run_dir}")
    url = f"http://localhost:3000/dev/creative-eval/{run_dir.name}"
    print(f"review: {url}")
    if open_browser:
        opened = webbrowser.open(url)
        if not opened:
            print(
                "could not open a browser; start the frontend (`npm run dev`) "
                "and visit the URL above"
            )


def _run_experiment(args: argparse.Namespace) -> int:
    experiments_dir = args.experiments_dir or EXPERIMENTS_DIR
    cases_dir = args.cases_dir or CASES_DIR
    runs_dir = args.runs_dir or RUNS_DIR
    try:
        experiment = load_experiment(args.experiment, experiments_dir=experiments_dir)
        jobs: list[SimpleNamespace] = []
        for item in experiment["cases"]:
            case = load_case(item["case"], cases_dir=cases_dir)
            recipe_refs = list(item["recipes"])
            if item["mode"] == "fixed" and not recipe_refs:
                recipe_refs = list(case.get("fixed_recipes") or [])
            if item["mode"] == "fixed" and not recipe_refs:
                raise FixtureError(
                    f"fixed case {item['case']} needs recipes in the "
                    "manifest or fixture.fixed_recipes"
                )
            resolve_image(case, require=not args.dry_run)
            jobs.append(
                SimpleNamespace(case=case, item=item, recipe_refs=recipe_refs)
            )
    except FixtureError as error:
        print(error, file=sys.stderr)
        return 2

    plans: list[EvalPlan] = []
    for job in jobs:
        item = job.item
        recipes = (
            job.recipe_refs
            if item["mode"] == "fixed"
            else [{"style_id": "(director)", "template_id": "(director)"}] * 3
        )
        plans.append(
            build_plan(
                case_id=job.case["case_id"],
                mode=item["mode"],
                recipes=recipes,
                candidates=item["candidates"],
                quality_check=item["quality_check"],
                repair=item["repair"],
                story=item["story"],
                master_crop=item["master_crop"],
                provider=args.provider,
                paid=args.paid,
                label=args.label or experiment["experiment_id"],
                concurrency=args.concurrency,
                experiment_id=experiment["experiment_id"],
            )
        )

    print(render_batch_plan(experiment["experiment_id"], plans))
    for plan in plans:
        print()
        print(render_plan(plan))

    refused = _paid_gates(
        provider=args.provider,
        paid=args.paid,
        dry_run=args.dry_run,
        confirm=args.confirm,
        sweep=False,
        experiment=True,
        image_outputs=sum(plan.image_outputs for plan in plans),
        estimated_usd=sum((plan.estimated_image_usd for plan in plans), Decimal("0")),
        recipe_count=sum(len(plan.recipes) for plan in plans),
    )
    if refused is not None:
        return refused
    if args.dry_run:
        print("\n--dry-run: zero provider calls.")
        return 0

    provider, planner, architect = _providers(args.provider)

    async def batch() -> list[Path]:
        written: list[Path] = []
        for job, plan in zip(jobs, plans, strict=True):
            run_dir = await _run_one(
                case=job.case,
                plan=plan,
                recipe_refs=job.recipe_refs,
                provider=provider,
                planner=planner,
                architect=architect,
                runs_dir=runs_dir,
            )
            written.append(run_dir)
            print(f"wrote {run_dir}", flush=True)
        return written

    written = asyncio.run(batch())
    print(f"\nbatch {experiment['experiment_id']}: {len(written)} runs", flush=True)
    if written:
        print("review: http://localhost:3000/dev/creative-eval")
        if args.open_browser:
            webbrowser.open(
                f"http://localhost:3000/dev/creative-eval/{written[0].name}"
            )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.experiment:
        if args.case or args.mode:
            print("use --experiment or --case/--mode, not both", file=sys.stderr)
            return 2
        if args.recipes or args.all_styles or args.all_templates:
            print(
                "recipe overrides belong on experiment cases, not the CLI",
                file=sys.stderr,
            )
            return 2
        return _run_experiment(args)
    if not args.case or not args.mode:
        print("need --case and --mode, or --experiment", file=sys.stderr)
        return 2

    cases_dir = args.cases_dir or CASES_DIR
    runs_dir = args.runs_dir or RUNS_DIR

    try:
        case = load_case(args.case, cases_dir=cases_dir)
        recipe_refs = _recipes_for_mode(args, case)
        if args.mode == "fixed" and not recipe_refs:
            raise FixtureError("fixed mode needs fixture.fixed_recipes or --recipes")
        if args.mode == "fixed":
            resolve_image(case, require=not args.dry_run)
        elif not args.dry_run:
            resolve_image(case, require=True)
    except FixtureError as error:
        print(error, file=sys.stderr)
        return 2

    plan = build_plan(
        case_id=case["case_id"],
        mode=args.mode,
        recipes=recipe_refs
        if args.mode == "fixed"
        else [
            {"style_id": "(director)", "template_id": "(director)"}
        ]
        * 3,
        candidates=args.candidates,
        quality_check=args.quality_check,
        repair=args.repair,
        story=args.story,
        master_crop=args.master_crop,
        provider=args.provider,
        paid=args.paid,
        label=args.label or None,
        concurrency=args.concurrency,
    )
    print(render_plan(plan))

    refused = _paid_gates(
        provider=args.provider,
        paid=args.paid,
        dry_run=args.dry_run,
        confirm=args.confirm,
        sweep=bool(args.all_styles or args.all_templates),
        experiment=False,
        image_outputs=plan.image_outputs,
        estimated_usd=plan.estimated_image_usd,
        recipe_count=len(recipe_refs),
    )
    if refused is not None:
        return refused
    if args.dry_run:
        print("\n--dry-run: zero provider calls.")
        return 0

    provider, planner, architect = _providers(args.provider)
    run_dir = asyncio.run(
        _run_one(
            case=case,
            plan=plan,
            recipe_refs=recipe_refs,
            provider=provider,
            planner=planner,
            architect=architect,
            runs_dir=runs_dir,
        )
    )
    _print_review(run_dir, args.open_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
