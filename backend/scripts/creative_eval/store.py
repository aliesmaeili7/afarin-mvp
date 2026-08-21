"""Immutable creative-eval run directories."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.creative_eval.cases import RUNS_DIR

_SLUG = re.compile(r"[^a-zA-Z0-9._-]+")


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=json_default)
        + "\n",
        encoding="utf-8",
    )


def slug(value: str) -> str:
    cleaned = _SLUG.sub("-", value.strip()).strip("-")
    return cleaned[:60] or "run"


def allocate_run_dir(
    *,
    case_id: str,
    label: str | None,
    runs_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    root = runs_dir or RUNS_DIR
    root.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
    parts = [case_id]
    if label:
        parts.append(slug(label))
    suffix = "_".join(parts)
    existing = [
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith(f"{stamp}_")
    ]
    seq = 1
    for name in existing:
        rest = name[len(stamp) + 1 :]
        number, _, _ = rest.partition("_")
        if number.isdigit():
            seq = max(seq, int(number) + 1)
    while True:
        dest = root / f"{stamp}_{seq:03d}_{suffix}"
        try:
            dest.mkdir(parents=False, exist_ok=False)
            return dest
        except FileExistsError:
            seq += 1


def recipe_folder(index: int, style_id: str, template_id: str) -> str:
    return f"{index:02d}_{style_id}__{template_id}"
