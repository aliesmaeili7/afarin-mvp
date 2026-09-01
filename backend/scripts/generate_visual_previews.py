"""One-time visual preview library for the style/template picker.

These JPEGs are permanent UI assets, not campaign outputs. They are never
generated during a user request.

How to run (from backend/):

    uv run python -m scripts.generate_visual_previews --dry-run
    uv run python -m scripts.generate_visual_previews --live
    uv run python -m scripts.generate_visual_previews --live --skip-existing
    uv run python -m scripts.generate_visual_previews --live --ids anime,hero_product

Reference image:
    frontend/public/demo-product.png
    (neutral athletic sneaker; attached as the identity reference on every call)

This is a paid job: 14 style + 12 template images through the configured
OpenRouter image model, using the same reference-image path as creative mode.

Style previews keep one hero composition and vary look.
Template previews keep photoreal commercial look and vary the scene.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.content.visual_catalog import preview_prompt_of, public_catalog, templates as catalog_templates
from app.core.config import get_settings
from app.providers.image import get_image_provider
from app.providers.image.base import ImageProvider, ImageRequest
from app.providers.image.prompts import HARD_NEGATIVES

_STYLE_IDS = frozenset(
    {
        "photoreal_commercial",
        "fashion_editorial",
        "anime",
        "manga_illustrated",
        "render_3d",
        "clay",
        "collage",
        "surreal",
        "cinematic",
        "retro",
        "watercolor_illustration",
        "neon",
        "persian_miniature_inspired",
        "vintage_iranian_poster",
    }
)


def styles() -> list[dict]:
    return [item for item in catalog_templates() if item["id"] in _STYLE_IDS]


def templates() -> list[dict]:
    return [item for item in catalog_templates() if item["id"] not in _STYLE_IDS]


ROOT = Path(__file__).resolve().parents[2]
DEMO_PRODUCT = ROOT / "frontend" / "public" / "demo-product.png"
PUBLIC = ROOT / "frontend" / "public" / "visual-previews"
ASPECT = "4:5"
PREVIEW_MAX_WIDTH = 1280
REFERENCE_MAX_SIDE = 1600

IDENTITY = (
    "the attached image is the only product identity: one white athletic "
    "running shoe with navy blue side accent, white mesh upper, white "
    "overlays, white laces, navy collar lining, and a white foam midsole. "
    "keep this shoe broadly recognizable. do not invent a new colorway, "
    "a second shoe, extra logos, or packaging claims"
)

STYLE_COMPOSITION = (
    "fixed simple hero composition for a style library card: 4:5 advertising "
    "still, one shoe as the centered hero, lateral three-quarter view facing "
    "left like a catalog side shot not a head-on front view, sitting on a "
    "simple supporting surface, same camera height, same product scale, same "
    "framing, empty band at the bottom for overlay type. only the visual "
    "medium, lighting, and art direction change"
)

TEMPLATE_STYLE = (
    "keep a consistent photoreal commercial product-photography look: studio "
    "quality lighting, sharp realistic materials, natural color. do not "
    "switch into illustration, anime, clay, or collage unless the template "
    "itself is an illustrated scene. only the composition and scenario change"
)

PREVIEW_NEGATIVES = HARD_NEGATIVES + (
    "no readable brand names",
    "no artist names",
    "no franchise or movie-scene imitation",
    "no named IP",
    "no watermarks",
    "no national flags",
    "no religious calligraphy",
    "no mastheads",
)

# Extra look notes on top of catalog preview prompts. Composition stays locked.
STYLE_DIRECTION = {
    "photoreal_commercial": (
        "clean seamless studio sweep, even catalog lighting, sharp materials"
    ),
    "fashion_editorial": (
        "dramatic fashion-magazine lighting and grade, high contrast, "
        "stylish shadow, not a plain catalog packshot"
    ),
    "anime": (
        "modern anime-inspired product still, clean linework, vivid cel shading"
    ),
    "manga_illustrated": (
        "inked illustrated still, screentone texture, graphic black and limited accent"
    ),
    "render_3d": (
        "the attached photo is identity-only, do not copy its photographic look. "
        "output an obvious CGI product render: perfectly smooth digital materials, "
        "studio HDRI reflections, slightly unreal 3D visualization, not a camera photo"
    ),
    "clay": (
        "the attached photo is identity-only, do not copy its photographic look. "
        "output a stop-motion clay puppet of the shoe: lumpy plasticine, "
        "visible thumbprints and clay seams, matte handmade sculpture, "
        "not a real sneaker photograph"
    ),
    "collage": (
        "cut-paper collage of the shoe, torn print layers, graphic overlapping shapes"
    ),
    "surreal": (
        "dreamlike sky and impossible light around the same hero placement"
    ),
    "cinematic": (
        "dark filmic still, volumetric light, teal-and-orange grade, "
        "shallow depth of field, moody dusk atmosphere, "
        "not a bright white studio packshot"
    ),
    "retro": (
        "vintage analog-film color, grain, period commercial lighting, same hero frame"
    ),
    "watercolor_illustration": (
        "hand-painted watercolor still, pigment blooms, visible paper texture"
    ),
    "neon": (
        "night commercial still, cyan and magenta rim light, wet reflections"
    ),
    "persian_miniature_inspired": (
        "ornamental garden geometry and flat decorative color around the shoe, "
        "no calligraphy"
    ),
    "vintage_iranian_poster": (
        "vintage mid-century commercial poster from Iranian print shops, "
        "lithographic ink, bold geometric shapes, ochre cream and deep teal "
        "limited palette, decorative borders without writing, no national flags, "
        "no emblems, no calligraphy, no letters"
    ),
}

# Extra scene notes on top of catalog preview prompts. Style stays photoreal.
TEMPLATE_DIRECTION = {
    "hero_product": (
        "centered hero on a seamless studio sweep, large in frame, soft grounded shadow"
    ),
    "model_using": (
        "one person putting on or wearing the sneaker, product clearly visible, "
        "natural lifestyle pose"
    ),
    "product_pedestal": (
        "shoe displayed on a stone or marble plinth, gallery spotlight, simple set"
    ),
    "magazine_cover": (
        "magazine-cover composition with a large completely blank top third, "
        "fashion-cover framing and empty header space, "
        "critical: zero letters, zero numbers, zero masthead, "
        "do not write any magazine name"
    ),
    "giant_miniature_world": (
        "enormous shoe standing among a tiny city street, playful forced perspective, "
        "one shoe only"
    ),
    "cinematic_environment": (
        "shoe on wet dusk pavement with cinematic atmosphere, product still readable"
    ),
    "floating_product": (
        "shoe levitating in mid-air with elegant rim light and empty space around it"
    ),
    "flat_lay": (
        "overhead top-down camera, exactly one shoe, socks and a bottle as props, "
        "no second shoe, no cropped extra products"
    ),
    "character_poster": (
        "full-body or three-quarter view of one person as a campaign "
        "poster figure wearing or holding the sneaker, product clearly "
        "visible, empty band at the top, absolutely no letters or initials, "
        "shoe at normal human scale not giant"
    ),
    "illustrated_scene": (
        "the shoe placed inside a supporting outdoor running scene that feels drawn "
        "or painted, product remains the subject"
    ),
    "product_with_props": (
        "still-life of the shoe with relevant running props "
        "such as a bottle and towel, "
        "no extra product variants"
    ),
    "surreal_scale": (
        "the shoe as an impossibly large landscape object with tiny figures nearby, "
        "one shoe only"
    ),
}


@dataclass(frozen=True, slots=True)
class PreviewJob:
    kind: str
    item_id: str
    relative_path: str
    prompt: str

    def dest(self, public: Path) -> Path:
        return public / self.kind / f"{self.item_id}.jpg"


def build_style_prompt(item: dict) -> str:
    return _join(
        "permanent UI preview card, advertising still",
        "use the attached product photo as the identity reference",
        IDENTITY,
        STYLE_COMPOSITION,
        preview_prompt_of(item),
        STYLE_DIRECTION[item["id"]],
        f"leave a clear empty {item['default_text_safe_area']} area "
        "for later typography overlay",
        *PREVIEW_NEGATIVES,
    )


def build_template_prompt(item: dict) -> str:
    photoreal = next(
        row for row in styles() if row["id"] == "photoreal_commercial"
    )
    return _join(
        "permanent UI preview card, advertising still",
        "use the attached product photo as the identity reference",
        IDENTITY,
        TEMPLATE_STYLE,
        preview_prompt_of(photoreal),
        preview_prompt_of(item),
        TEMPLATE_DIRECTION[item["id"]],
        f"leave a clear empty {item['default_text_safe_area']} area "
        "for later typography overlay",
        *PREVIEW_NEGATIVES,
    )


def preview_jobs(
    *, only: str | None = None, ids: set[str] | None = None
) -> list[PreviewJob]:
    jobs: list[PreviewJob] = []
    if only in (None, "styles"):
        for item in styles():
            if ids is not None and item["id"] not in ids:
                continue
            jobs.append(
                PreviewJob(
                    kind="styles",
                    item_id=item["id"],
                    relative_path=item["preview_path"],
                    prompt=build_style_prompt(item),
                )
            )
    if only in (None, "templates"):
        for item in templates():
            if ids is not None and item["id"] not in ids:
                continue
            jobs.append(
                PreviewJob(
                    kind="templates",
                    item_id=item["id"],
                    relative_path=item["preview_path"],
                    prompt=build_template_prompt(item),
                )
            )
    return jobs


def write_catalog(public: Path = PUBLIC) -> Path:
    public.mkdir(parents=True, exist_ok=True)
    path = public / "catalog.json"
    path.write_text(
        json.dumps(public_catalog(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_placeholders(public: Path = PUBLIC) -> None:
    write_catalog(public)
    for index, item in enumerate(styles()):
        color = (40 + index * 12, 60, 90 + index * 8)
        _placeholder(public / "styles" / f"{item['id']}.jpg", color)
    for index, item in enumerate(templates()):
        color = (90, 50 + index * 10, 70)
        _placeholder(public / "templates" / f"{item['id']}.jpg", color)


def load_reference(path: Path = DEMO_PRODUCT) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"demo product image missing: {path}")
    image = Image.open(path).convert("RGB")
    image = _limit_side(image, REFERENCE_MAX_SIDE)
    return _jpeg_bytes(image, quality=92)


def to_preview_jpeg(content: bytes) -> bytes:
    image = Image.open(io.BytesIO(content)).convert("RGB")
    image = _crop_to_aspect(image, 4, 5)
    image = _limit_side(image, PREVIEW_MAX_WIDTH)
    return _jpeg_bytes(image, quality=88)


async def generate_all(
    jobs: list[PreviewJob],
    *,
    provider: ImageProvider,
    reference: bytes,
    public: Path = PUBLIC,
    skip_existing: bool = False,
    concurrency: int = 2,
) -> list[str]:
    settings = get_settings()
    public.mkdir(parents=True, exist_ok=True)
    (public / "styles").mkdir(parents=True, exist_ok=True)
    (public / "templates").mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))
    cost_lock = asyncio.Lock()
    failures: list[str] = []
    cost = Decimal("0")

    async def one(job: PreviewJob) -> None:
        nonlocal cost
        dest = job.dest(public)
        if skip_existing and dest.is_file() and dest.stat().st_size > 40_000:
            print(f"skip {job.kind}/{job.item_id}")
            return
        async with semaphore:
            print(f"generate {job.kind}/{job.item_id}")
            try:
                result = await provider.generate(
                    ImageRequest(
                        prompt=job.prompt,
                        aspect_ratio=ASPECT,
                        resolution=settings.image_resolution,
                        references=(reference,),
                        n=1,
                    )
                )
            except Exception as error:
                failures.append(f"{job.kind}/{job.item_id}: {error}")
                print(f"fail {job.kind}/{job.item_id}: {error}")
                return
            dest.write_bytes(to_preview_jpeg(result.images()[0]))
            if result.usage.cost_usd is not None:
                async with cost_lock:
                    cost += result.usage.cost_usd
            try:
                shown = dest.relative_to(ROOT)
            except ValueError:
                shown = dest
            print(
                f"wrote {shown} ({dest.stat().st_size} bytes, "
                f"{result.usage.latency_ms}ms)"
            )

    await asyncio.gather(*(one(job) for job in jobs))
    print(f"estimated cost_usd={cost}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-time paid job: generate permanent style/template preview "
            f"JPEGs from {DEMO_PRODUCT.relative_to(ROOT)}."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="paid OpenRouter generation using the demo product as reference",
    )
    parser.add_argument(
        "--placeholders",
        action="store_true",
        help="write local color placeholders instead of calling the image model",
    )
    parser.add_argument("--dry-run", action="store_true", help="print jobs only")
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="rewrite catalog.json from the backend catalog",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="do not regenerate JPEGs that already look like real assets",
    )
    parser.add_argument(
        "--only",
        choices=("styles", "templates"),
        help="generate just one library",
    )
    parser.add_argument(
        "--ids",
        default="",
        help="comma-separated style/template ids",
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--allow-stub",
        action="store_true",
        help="allow IMAGE_PROVIDER=stub (tests / dry local writes)",
    )
    args = parser.parse_args(argv)

    wanted = {item.strip() for item in args.ids.split(",") if item.strip()} or None
    jobs = preview_jobs(only=args.only, ids=wanted)

    if args.dry_run:
        for job in jobs:
            print(job.kind, job.item_id, job.relative_path)
        return 0

    if args.catalog_only:
        path = write_catalog()
        print(f"wrote {path}")
        return 0

    if args.placeholders:
        write_placeholders()
        print(f"wrote placeholders under {PUBLIC}")
        return 0

    if not args.live:
        parser.print_help()
        print(
            "\nRefusing to overwrite preview JPEGs. This is a one-time paid "
            "asset job. Pass --live to generate, --placeholders for color "
            "blocks, or --dry-run to list jobs."
        )
        return 2

    provider = get_image_provider()
    if provider.name == "stub" and not args.allow_stub:
        raise SystemExit(
            "Refusing IMAGE_PROVIDER=stub. Set IMAGE_PROVIDER=openrouter "
            "or pass --allow-stub for local fixture writes."
        )
    if provider.name == "openrouter" and not get_settings().openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required for --live")

    write_catalog()
    failures = asyncio.run(
        generate_all(
            jobs,
            provider=provider,
            reference=load_reference(),
            skip_existing=args.skip_existing,
            concurrency=args.concurrency,
        )
    )
    if failures:
        print("failed:")
        for row in failures:
            print(" ", row)
        return 1
    print(f"wrote {len(jobs)} previews under {PUBLIC}")
    return 0


def _join(*parts: str) -> str:
    return ", ".join(part for part in parts if part)


def _placeholder(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (640, 800), color)
    path.write_bytes(_jpeg_bytes(image, quality=85))


def _crop_to_aspect(
    image: Image.Image, width_ratio: int, height_ratio: int
) -> Image.Image:
    target = width_ratio / height_ratio
    current = image.width / image.height if image.height else 0
    if abs(current - target) < 0.02:
        return image
    if current > target:
        new_w = int(image.height * target)
        left = (image.width - new_w) // 2
        return image.crop((left, 0, left + new_w, image.height))
    new_h = int(image.width / target)
    top = (image.height - new_h) // 2
    return image.crop((0, top, image.width, top + new_h))


def _limit_side(image: Image.Image, max_side: int) -> Image.Image:
    longest = max(image.size)
    if longest <= max_side:
        return image
    scale = max_side / longest
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _jpeg_bytes(image: Image.Image, *, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
