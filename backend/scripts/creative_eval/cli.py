"""CLI for the internal creative evaluation lab."""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path
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
from scripts.creative_eval.plan import build_plan, render_plan
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
    parser.add_argument("--case", required=True, help="fixture case_id")
    parser.add_argument("--mode", required=True, choices=("fixed", "director"))
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
        help="required for --all-styles / --all-templates paid runs",
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--label", default="", help="prompt experiment label")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--cases-dir", type=Path, default=None)
    parser.add_argument("--runs-dir", type=Path, default=None)
    return parser


def _providers(name: str) -> tuple[Any, Any]:
    if name == "stub":
        from app.providers.image.stub import StubImageProvider
        from app.providers.vision.stub import StubVisualPlanner

        return StubImageProvider(), StubVisualPlanner()
    from app.core.config import get_settings
    from app.providers.image.openrouter.client import OpenRouterImageClient
    from app.providers.image.openrouter.provider import OpenRouterImageProvider
    from app.providers.llm.openrouter.client import OpenRouterClient
    from app.providers.vision.openrouter import OpenRouterVisualPlanner

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required for --provider openrouter")
    image = OpenRouterImageProvider(OpenRouterImageClient(settings), settings)
    planner = OpenRouterVisualPlanner(OpenRouterClient(settings), settings)
    return image, planner


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
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

    if args.dry_run:
        print("\n--dry-run: zero provider calls.")
        return 0

    if args.provider == "openrouter" and not args.paid:
        print(
            "\nRefusing paid generation. Pass --provider openrouter --paid "
            "to spend image/LLM budget, or --provider stub / --dry-run.",
            file=sys.stderr,
        )
        return 2

    if (
        args.provider == "openrouter"
        and (args.all_styles or args.all_templates)
        and not args.confirm
    ):
        print(
            "\nRefusing catalog sweep without --confirm. "
            f"{len(recipe_refs)} recipes, "
            f"~{plan.image_outputs} image outputs, "
            f"~${plan.estimated_image_usd}.",
            file=sys.stderr,
        )
        return 2

    provider, planner = _providers(args.provider)

    director_result = None
    recipes: list[dict] = []
    directions = None

    async def run() -> Path:
        nonlocal director_result, recipes, directions
        if args.mode == "director":
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
            recipes=recipes,
            directions=directions,
            director=director_result,
            runs_dir=runs_dir,
        )

    run_dir = asyncio.run(run())
    print(f"\nwrote {run_dir}")
    url = f"http://localhost:3000/dev/creative-eval/{run_dir.name}"
    print(f"review: {url}")
    if args.open_browser:
        opened = webbrowser.open(url)
        if not opened:
            print(
                "could not open a browser; start the frontend (`npm run dev`) "
                "and visit the URL above"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
