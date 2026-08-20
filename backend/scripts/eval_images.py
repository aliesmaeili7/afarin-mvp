"""
Generate empty 4:5 and 9:16 scenes for packshot-style briefs.

    uv run python -m scripts.eval_images

Writes JPEG files and a JSON scorecard under eval/out/images/.
Requires OPENROUTER_API_KEY. Does not send the product through the model.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.providers.image.base import ImageRequest
from app.providers.image.openrouter.client import OpenRouterImageClient
from app.providers.image.openrouter.provider import OpenRouterImageProvider
from app.providers.image.prompts import build_scene_prompt

BRIEFS_DIR = Path(__file__).resolve().parents[1] / "eval" / "briefs"
OUT_DIR = Path(__file__).resolve().parents[1] / "eval" / "out" / "images"

# Cosmetics, clothing, food — enough to judge empty-scene quality.
PACKSHOTS = ("soap", "scarf", "saffron")
ASPECTS = ("4:5", "9:16")


def load_briefs() -> list[dict]:
    wanted = set(PACKSHOTS)
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(BRIEFS_DIR.glob("*.json"))
        if path.stem in wanted
    ]


def _score(path: Path, aspect: str, prompt: str) -> dict:
    image = Image.open(path)
    width, height = image.size
    ratio = width / height if height else 0
    expected = 4 / 5 if aspect == "4:5" else 9 / 16
    return {
        "path": str(path.relative_to(OUT_DIR.parent.parent)),
        "format": image.format,
        "width": width,
        "height": height,
        "aspect_ok": abs(ratio - expected) < 0.15,
        "prompt_has_no_text": "no text" in prompt.lower(),
        "prompt_has_no_product": "no product" in prompt.lower(),
        "bytes": path.stat().st_size,
    }


async def run(model: str) -> dict:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    settings.image_model = model
    provider = OpenRouterImageProvider(OpenRouterImageClient(settings), settings)
    results = []
    for brief in load_briefs():
        concept = SimpleNamespace(
            visual_direction="commercial photography lighting, empty set",
            background_prompt=(
                brief.get("background_prompt")
                or "empty scene, atmosphere and surfaces only, no text"
            ),
        )
        campaign = SimpleNamespace(visual_style=brief["style"])
        prompt = build_scene_prompt(concept, campaign)
        row = {"id": brief["id"], "style": brief["style"], "prompt": prompt, "scenes": {}}
        for aspect in ASPECTS:
            result = await provider.generate(
                ImageRequest(prompt=prompt, aspect_ratio=aspect, resolution="2K")
            )
            slug = aspect.replace(":", "x")
            dest = OUT_DIR / brief["id"] / f"scene-{slug}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            image = Image.open(io.BytesIO(result.content)).convert("RGB")
            image.save(dest, format="JPEG", quality=90)
            row["scenes"][aspect] = _score(dest, aspect, prompt)
            row["scenes"][aspect]["cost_usd"] = (
                str(result.usage.cost_usd) if result.usage.cost_usd is not None else None
            )
            row["scenes"][aspect]["latency_ms"] = result.usage.latency_ms
        results.append(row)
    return {
        "model": model,
        "generated_at": datetime.now(UTC).isoformat(),
        "briefs": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    settings = get_settings()
    model = args.model or settings.image_model
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = asyncio.run(run(model))
    path = OUT_DIR / f"{model.replace('/', '_')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
