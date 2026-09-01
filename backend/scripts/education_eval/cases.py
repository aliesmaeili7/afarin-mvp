"""Educational eval fixtures, loaded from backend/eval/education/*.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CASES_DIR = Path(__file__).resolve().parents[2] / "eval" / "education"


@dataclass(frozen=True, slots=True)
class EducationCase:
    id: str
    label: str
    user_prompt: str
    note: str = ""
    expect_language: str | None = None
    theme: dict[str, Any] | None = field(default=None)


def load_cases(only: tuple[str, ...] = ()) -> list[EducationCase]:
    cases = [_case(path) for path in sorted(CASES_DIR.glob("*.json"))]
    if not only:
        return cases
    wanted = set(only)
    missing = wanted - {case.id for case in cases}
    if missing:
        raise SystemExit(f"unknown case id(s): {', '.join(sorted(missing))}")
    return [case for case in cases if case.id in wanted]


def case_ids() -> tuple[str, ...]:
    return tuple(case.id for case in load_cases())


def _case(path: Path) -> EducationCase:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return EducationCase(
        id=str(raw["id"]),
        label=str(raw.get("label") or raw["id"]),
        user_prompt=str(raw["user_prompt"]),
        note=str(raw.get("note") or ""),
        expect_language=raw.get("expect_language"),
        theme=raw.get("theme"),
    )
