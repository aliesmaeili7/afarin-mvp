"""
Educational smoke harness.

    uv run python -m scripts.education_eval            # stub, free
    uv run python -m scripts.education_eval --case en_photosynthesis
    uv run python -m scripts.education_eval --no-image # agent only
    uv run python -m scripts.education_eval --live     # real providers, costs money

Stub is the default and --live is the only way to spend money, so this can be
run in CI and during development without a bill.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from scripts.education_eval.cases import case_ids, load_cases
from scripts.education_eval.runner import (
    CaseOutcome,
    allocate_run_dir,
    run_case,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts.education_eval",
        description="Prompt -> Educational Agent -> final prompt -> image.",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        metavar="ID",
        help=f"run one case; repeatable. Available: {', '.join(case_ids())}",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="use the configured real providers instead of stubs (costs money)",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="stop after the agent; do not request an image",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory for run artifacts (default: eval/runs/education/<stamp>)",
    )
    parser.add_argument("--list", action="store_true", help="list case ids and exit")
    return parser


async def _run(args: argparse.Namespace) -> int:
    cases = load_cases(tuple(args.case))
    if args.out:
        run_dir = args.out
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = allocate_run_dir()

    outcomes: list[CaseOutcome] = []
    for case in cases:
        outcome, detail = await run_case(case, with_image=not args.no_image)
        outcomes.append(outcome)
        write_json(run_dir / f"{case.id}.json", detail)
        _print_row(outcome)

    summary = {
        "live": bool(args.live),
        "with_image": not args.no_image,
        "total": len(outcomes),
        "passed": sum(1 for item in outcomes if item.ok),
        "cases": [item.as_dict() for item in outcomes],
    }
    write_json(run_dir / "summary.json", summary)

    failed = [item for item in outcomes if not item.ok]
    print(f"\n{summary['passed']}/{summary['total']} ok   artifacts: {run_dir}")
    for item in failed:
        for error in item.errors:
            print(f"  {item.case_id}: {error}")
    return 1 if failed else 0


def _print_row(outcome: CaseOutcome) -> None:
    mark = "ok  " if outcome.ok else "FAIL"
    print(
        f"{mark} {outcome.case_id:<28} lang={outcome.language or '?':<3} "
        f"prompt={outcome.prompt_chars:>4}c "
        f"images={outcome.image_count} retry={int(outcome.retry_used)} "
        f"{outcome.wall_time_ms:>5}ms  {outcome.theme_name or ''}"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        for case in load_cases():
            print(f"{case.id:<28} {case.label}")
        return 0

    if not args.live:
        # Set before any provider factory is touched, so a developer's real
        # .env cannot turn a smoke run into a paid one.
        os.environ["CONTENT_PROVIDER"] = "stub"
        os.environ["IMAGE_PROVIDER"] = "stub"
        from app.core.config import get_settings

        get_settings.cache_clear()

    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
