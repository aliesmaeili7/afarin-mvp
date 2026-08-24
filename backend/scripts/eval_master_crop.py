"""Compare dedicated 4:5+Story generation vs a 9:16 master cropped to 4:5.

    uv run python -m scripts.eval_master_crop
    uv run python -m scripts.eval_master_crop --synthetic

Writes side-by-side JPEGs and a JSON scorecard under eval/out/master_crop/.
Does not change production generation (`image_compose_strategy` stays unused).

Live mode needs OPENROUTER_API_KEY. `--synthetic` paints solid frames so the
crop math can be checked without calling a provider.
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

from PIL import Image, ImageDraw, ImageFont, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.image.base import ImageRequest
from app.providers.image.creative_prompts import compile_architect_result
from app.providers.image.prompts import build_scene_prompt
from app.providers.vision.stub import stub_architect_result
from app.services.campaigns.master_crop import MASTER_NOTE, central_4x5_crop

BRIEFS_DIR = Path(__file__).resolve().parents[1] / "eval" / "briefs"
OUT_DIR = Path(__file__).resolve().parents[1] / "eval" / "out" / "master_crop"

# Cosmetics, clothing, food — the three product families in the plan.
PACKSHOTS = ("soap", "scarf", "saffron")
CREATIVE_RECIPE = {
    "style_id": "photoreal_commercial",
    "template_id": "hero_product",
    "scene_direction": "studio hero, product in a central 4:5-safe region",
    "text_safe_area": "bottom",
    "identity_constraints": ["keep major colors", "keep silhouette"],
}


def load_briefs() -> list[dict]:
    wanted = set(PACKSHOTS)
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(BRIEFS_DIR.glob("*.json"))
        if path.stem in wanted
    ]


def _aspect(image: Image.Image) -> float:
    return image.width / image.height if image.height else 0


def _band_stats(image: Image.Image, *, edge: str, fraction: float = 0.18) -> dict:
    gray = image.convert("L")
    width, height = gray.size
    if edge == "bottom":
        box = (0, int(height * (1 - fraction)), width, height)
    else:
        box = (0, 0, width, int(height * fraction))
    band = gray.crop(box)
    stats = ImageStat.Stat(band)
    full = ImageStat.Stat(gray)
    return {
        "mean": round(stats.mean[0], 2),
        "stddev": round(stats.stddev[0], 2),
        "full_mean": round(full.mean[0], 2),
        "full_stddev": round(full.stddev[0], 2),
        "emptier_than_frame": stats.stddev[0] < full.stddev[0],
    }


def _center_mass(image: Image.Image) -> dict:
    gray = image.convert("L")
    width, height = gray.size
    inset_x, inset_y = int(width * 0.15), int(height * 0.15)
    center = gray.crop((inset_x, inset_y, width - inset_x, height - inset_y))
    stats = ImageStat.Stat(center)
    full = ImageStat.Stat(gray)
    return {
        "center_stddev": round(stats.stddev[0], 2),
        "frame_stddev": round(full.stddev[0], 2),
        "subject_likely_centered": stats.stddev[0] >= full.stddev[0] * 0.85,
    }


def score_frame(path: Path, expected: str) -> dict:
    image = Image.open(path)
    ratio = _aspect(image)
    expected_ratio = 4 / 5 if expected == "4:5" else 9 / 16
    return {
        "path": str(path.relative_to(OUT_DIR.parent.parent)),
        "width": image.width,
        "height": image.height,
        "aspect": round(ratio, 4),
        "aspect_ok": abs(ratio - expected_ratio) < 0.08,
        "text_safe_bottom": _band_stats(image, edge="bottom"),
        "composition": _center_mass(image),
        "bytes": path.stat().st_size,
    }


def side_by_side(left: Image.Image, right: Image.Image, labels: tuple[str, str]) -> Image.Image:
    height = 640
    def _fit(image: Image.Image) -> Image.Image:
        scale = height / image.height
        return image.resize(
            (max(1, int(image.width * scale)), height), Image.Resampling.LANCZOS
        )

    a, b = _fit(left.convert("RGB")), _fit(right.convert("RGB"))
    gap, label_h = 12, 36
    canvas = Image.new(
        "RGB", (a.width + b.width + gap, height + label_h), (18, 18, 22)
    )
    canvas.paste(a, (0, label_h))
    canvas.paste(b, (a.width + gap, label_h))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((8, 10), labels[0], fill=(240, 240, 240), font=font)
    draw.text((a.width + gap + 8, 10), labels[1], fill=(240, 240, 240), font=font)
    return canvas


def _campaign(brief: dict, prompt_extra: str = "") -> tuple[SimpleNamespace, SimpleNamespace]:
    concept = SimpleNamespace(
        visual_direction=brief.get("visual_direction")
        or "commercial photography lighting",
        background_prompt=(
            brief.get("background_prompt")
            or "empty scene, atmosphere and surfaces only, no text"
        )
        + (f", {prompt_extra}" if prompt_extra else ""),
        headline_fa="",
        title_fa="",
        description_fa="",
    )
    campaign = SimpleNamespace(visual_style=brief["style"])
    return concept, campaign


def _synthetic(aspect: str, tone: int) -> bytes:
    width, height = (1080, 1350) if aspect == "4:5" else (1080, 1920)
    image = Image.new("RGB", (width, height), (tone, 40, 80))
    draw = ImageDraw.Draw(image)
    # Subject blob in the 4:5-safe center of a 9:16 canvas (or the full 4:5 frame).
    safe_h = int(width * 5 / 4)
    top = (height - safe_h) // 2 if height > safe_h else 0
    box = (width * 0.28, top + safe_h * 0.22, width * 0.72, top + safe_h * 0.72)
    draw.ellipse(box, fill=(220, 200, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


class _SyntheticProvider:
    name = "synthetic"
    model = "synthetic"

    async def generate(self, request: ImageRequest):
        content = _synthetic(request.aspect_ratio, 70 if request.aspect_ratio == "4:5" else 50)
        return SimpleNamespace(
            content=content,
            usage=SimpleNamespace(cost_usd=None, latency_ms=0),
        )


async def _provider(live: bool):
    if not live:
        return _SyntheticProvider()
    from app.core.config import get_settings
    from app.providers.image.openrouter.client import OpenRouterImageClient
    from app.providers.image.openrouter.provider import OpenRouterImageProvider

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required (or pass --synthetic)")
    return OpenRouterImageProvider(OpenRouterImageClient(settings), settings)


async def _save(content: bytes, dest: Path) -> Image.Image:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(io.BytesIO(content)).convert("RGB")
    image.save(dest, format="JPEG", quality=90)
    return image


async def run_case(
    provider, brief: dict, mode: str, live: bool
) -> dict:
    slug = f"{brief['id']}_{mode}"
    folder = OUT_DIR / slug
    concept, campaign = _campaign(brief)
    if mode == "accurate":
        dedicated_prompt = build_scene_prompt(concept, campaign)
        master_prompt = build_scene_prompt(
            concept, campaign
        ) + ", " + MASTER_NOTE
    else:
        dedicated_prompt = compile_architect_result(stub_architect_result()).candidates[
            0
        ].compiled_prompt
        master_prompt = dedicated_prompt + ", " + MASTER_NOTE

    feed_a = await provider.generate(
        ImageRequest(prompt=dedicated_prompt, aspect_ratio="4:5")
    )
    story_a = await provider.generate(
        ImageRequest(prompt=dedicated_prompt, aspect_ratio="9:16")
    )
    master_b = await provider.generate(
        ImageRequest(prompt=master_prompt, aspect_ratio="9:16")
    )

    feed_path = folder / "a_feed_45.jpg"
    story_path = folder / "a_story_916.jpg"
    master_path = folder / "b_master_916.jpg"
    crop_path = folder / "b_feed_crop_45.jpg"
    compare_feed = folder / "compare_feed.jpg"
    compare_story = folder / "compare_story.jpg"

    feed_img = await _save(feed_a.content, feed_path)
    story_img = await _save(story_a.content, story_path)
    master_img = await _save(master_b.content, master_path)
    crop_img = central_4x5_crop(master_img)
    crop_img.save(crop_path, format="JPEG", quality=90)

    side_by_side(feed_img, crop_img, ("A dedicated 4:5", "B 9:16→4:5 crop")).save(
        compare_feed, format="JPEG", quality=90
    )
    side_by_side(story_img, master_img, ("A dedicated 9:16", "B 9:16 master")).save(
        compare_story, format="JPEG", quality=90
    )

    return {
        "id": brief["id"],
        "mode": mode,
        "live": live,
        "product_name": brief["product_name"],
        "prompts": {
            "dedicated": dedicated_prompt,
            "master": master_prompt,
        },
        "a_dedicated": {
            "feed": score_frame(feed_path, "4:5"),
            "story": score_frame(story_path, "9:16"),
            "cost_usd": {
                "feed": str(getattr(feed_a.usage, "cost_usd", None)),
                "story": str(getattr(story_a.usage, "cost_usd", None)),
            },
        },
        "b_master_crop": {
            "master": score_frame(master_path, "9:16"),
            "feed_crop": score_frame(crop_path, "4:5"),
            "story": score_frame(master_path, "9:16"),
            "cost_usd": str(getattr(master_b.usage, "cost_usd", None)),
        },
        "identity": {
            "note": (
                "Heuristic only: center contrast vs full frame, plus an empty "
                "bottom band for type. Human review of compare_*.jpg is required."
            ),
            "a_feed_centered": score_frame(feed_path, "4:5")["composition"][
                "subject_likely_centered"
            ],
            "b_crop_centered": score_frame(crop_path, "4:5")["composition"][
                "subject_likely_centered"
            ],
        },
    }


async def run(live: bool) -> dict:
    provider = await _provider(live)
    results = []
    for brief in load_briefs():
        for mode in ("accurate", "creative"):
            results.append(await run_case(provider, brief, mode, live))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "strategy_flag": "image_compose_strategy is unused in production",
        "live": live,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Skip the image provider and paint geometric stand-ins",
    )
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = asyncio.run(run(live=not args.synthetic))
    path = OUT_DIR / ("synthetic.json" if args.synthetic else "scorecard.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
