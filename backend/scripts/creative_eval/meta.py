"""Sanitized reproducibility metadata for eval runs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from app.content import visual_catalog
from app.core.config import get_settings
from app.providers.image.creative_prompts import CREATIVE_PROMPT_VERSION

REPO_ROOT = Path(__file__).resolve().parents[3]


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def payload_sha256(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def git_state() -> dict[str, Any]:
    commit = _git(["rev-parse", "HEAD"])
    porcelain = _git(["status", "--porcelain"])
    dirty = None if porcelain is None else bool(porcelain.strip())
    return {"commit": commit, "dirty": dirty}


def reproducibility(
    *,
    case: dict[str, Any],
    provider: Any,
    planner: Any,
) -> dict[str, Any]:
    settings = get_settings()
    fixture = {key: value for key, value in case.items() if not str(key).startswith("_")}
    planner_model = getattr(planner, "model", None) or settings.planner_model
    return {
        "git": git_state(),
        "image_model": getattr(provider, "model", None) or settings.image_model,
        "director_model": planner_model,
        "qc_model": planner_model,
        "provider_params": {
            "image_resolution": settings.image_resolution,
            "candidate_aspect": "4:5",
            "story_aspect": "9:16",
            "seed_supported": False,
        },
        "fixture_sha256": payload_sha256(fixture),
        "catalog_sha256": file_sha256(
            Path(visual_catalog.__file__).with_name("visual_catalog.json")
        ),
        "prompt_version": CREATIVE_PROMPT_VERSION,
    }


def _git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or ""
