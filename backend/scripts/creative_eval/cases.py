"""Creative eval fixture loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.content.visual_catalog import style_ids, template_ids

OBJECTIVES = frozenset(
    {"sell_product", "new_product", "promotion", "brand_awareness"}
)
VISUAL_STYLES = frozenset(
    {"luxury", "minimal", "friendly", "bold", "persian_traditional", "modern"}
)

EVAL_ROOT = Path(__file__).resolve().parents[2] / "eval"
CASES_DIR = EVAL_ROOT / "creative_cases"
ASSETS_DIR = EVAL_ROOT / "assets"
RUNS_DIR = EVAL_ROOT / "creative_runs"


class FixtureError(ValueError):
    pass


def load_case(case_id: str, *, cases_dir: Path | None = None) -> dict[str, Any]:
    folder = cases_dir or CASES_DIR
    path = folder / f"{case_id}.json"
    if not path.is_file():
        matches = list(folder.glob("*.json"))
        for candidate in matches:
            data = _read_json(candidate)
            if data.get("case_id") == case_id:
                return validate_case(data, path=candidate)
        names = ", ".join(p.stem for p in sorted(matches)) or "(none)"
        raise FixtureError(f"unknown case {case_id!r}; available: {names}")
    return validate_case(_read_json(path), path=path)


def validate_case(data: dict[str, Any], *, path: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise FixtureError(f"{path}: fixture must be a JSON object")
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise FixtureError(f"{path}: case_id is required")
    product = data.get("product")
    if not isinstance(product, dict):
        raise FixtureError(f"{path}: product object is required")
    name = product.get("name")
    if not isinstance(name, str) or not name.strip():
        raise FixtureError(f"{path}: product.name is required")
    objective = data.get("objective")
    if objective not in OBJECTIVES:
        raise FixtureError(
            f"{path}: objective must be one of {sorted(OBJECTIVES)}"
        )
    visual_style = data.get("visual_style")
    if visual_style not in VISUAL_STYLES:
        raise FixtureError(
            f"{path}: visual_style must be one of {sorted(VISUAL_STYLES)}"
        )
    category = data.get("category")
    if category is not None and (
        not isinstance(category, str) or not category.strip()
    ):
        raise FixtureError(f"{path}: category must be a non-empty string")
    image_field = data.get("product_image")
    if not isinstance(image_field, str) or not image_field.strip():
        raise FixtureError(f"{path}: product_image is required")
    image_path = (path.parent / image_field).resolve()
    recipes = data.get("fixed_recipes") or []
    if recipes and not isinstance(recipes, list):
        raise FixtureError(f"{path}: fixed_recipes must be a list")
    for index, item in enumerate(recipes):
        _validate_recipe_ref(item, where=f"{path} fixed_recipes[{index}]")
    data = dict(data)
    data["_path"] = str(path)
    data["_image_path"] = str(image_path)
    return data


def resolve_image(case: dict[str, Any], *, require: bool) -> Path:
    path = Path(case["_image_path"])
    if path.is_file():
        return path
    if require:
        raise FixtureError(f"product image missing: {path}")
    return path


def parse_recipes(raw: str) -> list[dict[str, str]]:
    recipes: list[dict[str, str]] = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        if ":" not in item:
            raise FixtureError(
                f"recipe {item!r} must be style_id:template_id"
            )
        style_id, template_id = item.split(":", 1)
        recipes.append(
            {
                "style_id": style_id.strip(),
                "template_id": template_id.strip(),
            }
        )
        _validate_recipe_ref(recipes[-1], where=item)
    if not recipes:
        raise FixtureError("no recipes parsed")
    return recipes


def catalog_recipes(
    *,
    all_styles: bool,
    all_templates: bool,
    style_id: str | None,
    template_id: str | None,
) -> list[dict[str, str]]:
    if all_styles and all_templates:
        raise FixtureError(
            "refuse combining --all-styles and --all-templates "
            "(that would be 14×12 paid generations)"
        )
    if all_styles:
        if not template_id:
            raise FixtureError("--all-styles requires --template")
        if template_id not in template_ids():
            raise FixtureError(f"unknown template_id {template_id!r}")
        return [
            {"style_id": item, "template_id": template_id} for item in style_ids()
        ]
    if all_templates:
        if not style_id:
            raise FixtureError("--all-templates requires --style")
        if style_id not in style_ids():
            raise FixtureError(f"unknown style_id {style_id!r}")
        return [
            {"style_id": style_id, "template_id": item} for item in template_ids()
        ]
    return []


def _validate_recipe_ref(item: Any, *, where: str) -> None:
    if not isinstance(item, dict):
        raise FixtureError(f"{where}: recipe must be an object")
    style_id = item.get("style_id")
    template_id = item.get("template_id")
    if style_id not in style_ids():
        raise FixtureError(f"{where}: unknown style_id {style_id!r}")
    if template_id not in template_ids():
        raise FixtureError(f"{where}: unknown template_id {template_id!r}")


def _read_json(path: Path) -> dict[str, Any]:
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FixtureError(f"{path}: invalid JSON ({error})") from error
    if not isinstance(data, dict):
        raise FixtureError(f"{path}: fixture must be a JSON object")
    return data
