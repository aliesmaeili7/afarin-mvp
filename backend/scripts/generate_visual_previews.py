"""Write style/template preview JPEGs.

Default: local placeholders (no paid API). Pass --live to generate with the
configured image model. Never called from campaign requests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from app.content.visual_catalog import public_catalog, styles, templates

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public" / "visual-previews"


def _placeholder(path: Path, label: str, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (640, 800), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 600, 760), outline=(255, 255, 255), width=6)
    draw.rectangle((80, 520, 560, 720), fill=(0, 0, 0))
    path.write_bytes(_jpeg(image))


def _jpeg(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def write_placeholders() -> None:
    catalog = public_catalog()
    (PUBLIC).mkdir(parents=True, exist_ok=True)
    (PUBLIC / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for index, item in enumerate(styles()):
        color = (40 + index * 12, 60, 90 + index * 8)
        dest = ROOT / "frontend" / "public" / item["preview_path"].lstrip("/")
        _placeholder(dest, item["id"], color)
    for index, item in enumerate(templates()):
        color = (90, 50 + index * 10, 70)
        dest = ROOT / "frontend" / "public" / item["preview_path"].lstrip("/")
        _placeholder(dest, item["id"], color)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="paid OpenRouter generation",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        for item in styles() + templates():
            print(item["id"], item["preview_path"])
        return
    if args.live:
        raise SystemExit(
            "Use IMAGE_PROVIDER=openrouter and extend this script "
            "to call ImageProvider."
        )
    write_placeholders()
    print(f"wrote placeholders under {PUBLIC}")


if __name__ == "__main__":
    main()
