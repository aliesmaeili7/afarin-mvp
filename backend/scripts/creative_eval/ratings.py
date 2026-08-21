"""Human rating helpers for creative eval runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.creative_eval.store import write_json

SCORE_FIELDS = (
    "overall",
    "identity",
    "attractiveness",
    "style_match",
    "template_match",
    "commercial",
)
FLAGS = (
    "random_text_logo",
    "product_changed",
    "anatomy_artifact",
    "duplicated_product",
    "bad_composition",
    "boring_generic",
    "style_mismatch",
    "template_mismatch",
)


def empty_ratings() -> dict[str, Any]:
    return {"candidates": {}, "director": {}}


def load_ratings(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "ratings.json"
    if not path.is_file():
        return empty_ratings()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return empty_ratings()
    data.setdefault("candidates", {})
    data.setdefault("director", {})
    return data


def save_ratings(run_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        "candidates": payload.get("candidates") or {},
        "director": payload.get("director") or {},
    }
    write_json(run_dir / "ratings.json", cleaned)
    return cleaned


def recipe_summaries(runs_dir: Path) -> list[dict[str, Any]]:
    import json

    buckets: dict[str, dict[str, Any]] = {}
    if not runs_dir.is_dir():
        return []
    for run in sorted(runs_dir.iterdir()):
        ratings_path = run / "ratings.json"
        if not ratings_path.is_file():
            continue
        ratings = json.loads(ratings_path.read_text(encoding="utf-8"))
        candidates = ratings.get("candidates") or {}
        if not isinstance(candidates, dict):
            continue
        for key, row in candidates.items():
            if not isinstance(row, dict):
                continue
            recipe_key = str(key).rsplit(":", 1)[0]
            bucket = buckets.setdefault(
                recipe_key,
                {
                    "recipe": recipe_key,
                    "n": 0,
                    "overall": 0.0,
                    "identity": 0.0,
                    "commercial": 0.0,
                    "hard_fail": 0,
                    "hard_fail_n": 0,
                },
            )
            overall = row.get("overall")
            if isinstance(overall, int):
                bucket["n"] += 1
                bucket["overall"] += overall
                identity = row.get("identity")
                commercial = row.get("commercial")
                if isinstance(identity, int):
                    bucket["identity"] += identity
                if isinstance(commercial, int):
                    bucket["commercial"] += commercial
            quality_path = _quality_path(run, recipe_key)
            if quality_path is not None:
                quality = json.loads(quality_path.read_text(encoding="utf-8"))
                slot = _slot_from_key(str(key))
                for item in quality.get("candidates") or []:
                    if item.get("slot") == slot:
                        bucket["hard_fail_n"] += 1
                        if item.get("hard_failed"):
                            bucket["hard_fail"] += 1
    summary = []
    for recipe_key, bucket in sorted(buckets.items()):
        n = bucket["n"] or 1
        hard_n = bucket["hard_fail_n"]
        summary.append(
            {
                "recipe": recipe_key,
                "rated": bucket["n"],
                "avg_overall": round(bucket["overall"] / n, 2) if bucket["n"] else None,
                "avg_identity": round(bucket["identity"] / n, 2) if bucket["n"] else None,
                "avg_commercial": (
                    round(bucket["commercial"] / n, 2) if bucket["n"] else None
                ),
                "hard_fail_rate": (
                    round(bucket["hard_fail"] / hard_n, 2) if hard_n else None
                ),
            }
        )
    return summary


def _slot_from_key(key: str) -> int:
    _, _, slot = key.rpartition(":")
    try:
        return int(slot)
    except ValueError:
        return 1


def _quality_path(run: Path, recipe_key: str) -> Path | None:
    recipes = run / "recipes"
    if not recipes.is_dir():
        return None
    # recipe_key is folder name or folder: we stored as folder:slot
    folder = recipes / recipe_key
    quality = folder / "quality.json"
    if quality.is_file():
        return quality
    for child in recipes.iterdir():
        if child.name.endswith(recipe_key) or child.name == recipe_key:
            path = child / "quality.json"
            if path.is_file():
                return path
    return None
