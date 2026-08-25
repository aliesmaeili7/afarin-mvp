"""Wall-clock timing for creative eval. Never sum provider latency_ms."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.creative_eval.store import write_json


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_summary(
    *,
    wall_ms: int,
    candidate_count: int,
    quality_check: bool,
    repairs: int = 0,
    story: int = 0,
) -> str:
    seconds = wall_ms / 1000
    parts = [f"{seconds:.1f} s wall-clock for {candidate_count} candidate images"]
    extras: list[str] = []
    if quality_check:
        extras.append("QC")
    if repairs:
        extras.append(f"{repairs} repair")
    if story:
        extras.append("story")
    if extras:
        parts.append("+ " + " + ".join(extras))
    return " ".join(parts)


def write_run_timing(
    run_dir: Path,
    *,
    started_at: datetime,
    started_perf: float,
    finished_perf: float,
    plan: Any,
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    finished_at = utc_now()
    wall_ms = max(0, int(round((finished_perf - started_perf) * 1000)))
    requested = int(getattr(plan, "candidates", 0) or 0) * max(1, len(summaries) or 1)
    if summaries:
        requested = int(getattr(plan, "candidates", 0) or 0) * len(summaries)
    successful = sum(int(row.get("candidates") or 0) for row in summaries)
    repairs = sum(int(row.get("repairs") or 0) for row in summaries)
    stories = sum(1 for row in summaries if row.get("story"))
    paid = sum(int(row.get("image_outputs") or 0) for row in summaries)
    payload = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "wall_time_ms": wall_ms,
        "requested_candidates": requested,
        "successful_candidates": successful,
        "paid_image_outputs": paid,
        "repair_outputs": repairs,
        "story_outputs": stories,
        "summary": format_summary(
            wall_ms=wall_ms,
            candidate_count=successful,
            quality_check=bool(getattr(plan, "quality_check", False)),
            repairs=repairs,
            story=stories,
        ),
    }
    write_json(run_dir / "timing.json", payload)
    return payload


def write_batch_timing(
    runs_dir: Path,
    *,
    experiment_id: str,
    started_at: datetime,
    started_perf: float,
    finished_perf: float,
    runs: list[dict[str, Any]],
) -> Path:
    finished_at = utc_now()
    wall_ms = max(0, int(round((finished_perf - started_perf) * 1000)))
    folder = runs_dir / "_batches"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y-%m-%dT%H%M%SZ")
    path = folder / f"{stamp}_{experiment_id}.json"
    payload = {
        "experiment_id": experiment_id,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "wall_time_ms": wall_ms,
        "summary": f"{wall_ms / 1000:.1f} s wall-clock for {len(runs)} runs",
        "runs": runs,
    }
    write_json(path, payload)
    return path
