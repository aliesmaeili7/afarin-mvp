"""Paid bakeoff: Seedream vs other OpenRouter image models.

Run explicitly: uv run python -m scripts.eval_image_models
Never imported by campaign code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.providers.image.base import ImageRequest
from app.providers.image.openrouter.client import OpenRouterImageClient
from app.providers.image.openrouter.provider import OpenRouterImageProvider

DEFAULT_MODELS = (
    "bytedance-seed/seedream-4.5",
)


async def run(models: list[str], prompt: str) -> dict:
    settings = get_settings()
    results = []
    for model in models:
        settings.image_model = model
        provider = OpenRouterImageProvider(OpenRouterImageClient(settings), settings)
        request = ImageRequest(prompt=prompt, aspect_ratio="4:5", n=1)
        result = await provider.generate(request)
        results.append(
            {
                "model": model,
                "bytes": len(result.content),
                "cost_usd": str(result.usage.cost_usd),
                "latency_ms": result.usage.latency_ms,
            }
        )
    return {"prompt": prompt, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument(
        "--prompt",
        default="photoreal commercial hero product, empty type band, no text",
    )
    args = parser.parse_args()
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    payload = asyncio.run(run(models, args.prompt))
    out = Path(__file__).resolve().parents[1] / "eval" / "out" / "image_models.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
