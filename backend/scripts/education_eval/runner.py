"""
Runs each fixture through the real educational core.

There is no database here: this calls the same `plan_validated_post` and
`generate_post_image` the API uses, which is what makes the smoke run
meaningful rather than a parallel implementation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.education import core
from app.services.education.render_spec import build_render_spec
from app.services.education.themes import agent_theme_input, theme_from_agent
from scripts.education_eval.cases import EducationCase

RUNS_DIR = Path(__file__).resolve().parents[2] / "eval" / "runs" / "education"


@dataclass(slots=True)
class CaseOutcome:
    case_id: str
    label: str
    ok: bool
    language: str | None = None
    prompt_chars: int = 0
    image_count: int = 0
    image_bytes: int = 0
    retry_used: bool = False
    wall_time_ms: int = 0
    theme_name: str | None = None
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "label": self.label,
            "ok": self.ok,
            "language": self.language,
            "prompt_chars": self.prompt_chars,
            "image_count": self.image_count,
            "image_bytes": self.image_bytes,
            "retry_used": self.retry_used,
            "wall_time_ms": self.wall_time_ms,
            "theme_name": self.theme_name,
            "errors": list(self.errors),
        }


async def run_case(
    case: EducationCase, *, with_image: bool = True
) -> tuple[CaseOutcome, dict[str, Any]]:
    started = time.perf_counter()
    outcome = CaseOutcome(case_id=case.id, label=case.label, ok=False)
    detail: dict[str, Any] = {"case": case.id, "user_prompt": case.user_prompt}

    theme_input = agent_theme_input(case.theme)
    try:
        planned = await core.plan_validated_post(
            user_prompt=case.user_prompt, selected_theme=theme_input
        )
    except Exception as error:
        outcome.errors.append(f"agent failed: {error}")
        outcome.wall_time_ms = _elapsed(started)
        detail["error"] = str(error)
        return outcome, detail

    result = planned.result
    outcome.language = result.language
    outcome.prompt_chars = len(result.final_prompt)
    outcome.retry_used = planned.retry_used

    effective_theme = theme_input or theme_from_agent(result.theme)
    outcome.theme_name = str(effective_theme.get("name") or "")
    detail["agent"] = planned.as_dict()
    detail["effective_theme"] = effective_theme

    if case.expect_language and result.language != case.expect_language:
        outcome.errors.append(
            f"expected language {case.expect_language}, got {result.language}"
        )

    if with_image:
        try:
            image = await core.generate_post_image(result.final_prompt)
        except Exception as error:
            outcome.errors.append(f"image failed: {error}")
            outcome.wall_time_ms = _elapsed(started)
            detail["error"] = str(error)
            return outcome, detail
        outcome.image_count = core.EDUCATION_IMAGE_COUNT
        outcome.image_bytes = len(image.content)
        detail["image"] = {
            "bytes": len(image.content),
            "media_type": image.media_type,
        }
        detail["render_spec"] = build_render_spec(image_path="eval://image")

    outcome.wall_time_ms = _elapsed(started)
    outcome.ok = not outcome.errors
    return outcome, detail


def allocate_run_dir(root: Path | None = None) -> Path:
    """A timestamped directory, suffixed if two runs land in the same second."""
    base = root or RUNS_DIR
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    candidate = base / stamp
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stamp}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _elapsed(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
