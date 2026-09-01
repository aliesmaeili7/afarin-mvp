"""
Guards the educational path against drifting back into the old architecture.

Phase 1 has one obvious route: prompt -> Educational Agent -> one image.
There is no Director, no Prompt Architect, no visual planner, no recipe set,
no candidate selection and no advertising text compositor. This test fails
loudly if any of that creeps back in through an import.
"""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

EDUCATION_MODULES = (
    BACKEND / "app" / "providers" / "education",
    BACKEND / "app" / "services" / "education",
    BACKEND / "app" / "content" / "education_themes.py",
    BACKEND / "app" / "api" / "v1" / "education.py",
    BACKEND / "app" / "schemas" / "education.py",
    BACKEND / "app" / "db" / "models" / "education.py",
    BACKEND / "scripts" / "education_eval",
)

#: Removed or advertising-only machinery. An educational module importing any of
#: these means the two paths have started to entangle.
FORBIDDEN_IMPORTS = (
    "app.services.campaigns.planner",
    "app.services.campaigns.recipes",
    "app.services.campaigns.render_strategy",
    "app.services.campaigns.product_composite",
    "app.services.campaigns.creative_core",
    "app.services.campaigns.creative",
    "app.services.campaigns.visuals",
    "app.services.campaigns.crop",
    "app.services.campaigns.cutout",
    "app.services.campaigns.master_crop",
    "app.services.campaigns.reference_prep",
    "app.services.campaigns.product_media",
    "app.services.campaigns.stages",
    "app.services.campaigns.summaries",
    "app.services.campaigns.materialize",
    "app.services.campaigns.text_layers",
    "app.providers.vision.architect_validate",
    "app.providers.vision.creative_validate",
    "app.providers.vision.prompts",
    "app.providers.vision.openrouter",
    "app.providers.vision.stub",
    "app.content.visual_catalog",
    "app.content.concepts",
    "app.content.backgrounds",
    "scripts.creative_eval",
)

#: Narrow, deliberate exceptions, each justified.
ALLOWED = {
    # LlmCallTrace and llm_usage_dict are generic telemetry shapes, not
    # advertising logic.
    "app.providers.vision.base",
    # Writes provider usage onto a generation_jobs row. Both paths share that
    # table, so they share the writer.
    "app.services.campaigns.jobs",
}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for target in EDUCATION_MODULES:
        if target.is_dir():
            files.extend(sorted(target.rglob("*.py")))
        elif target.exists():
            files.append(target)
    return files


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def test_education_modules_exist() -> None:
    """A silent zero-file scan would make the guard below meaningless."""
    files = _python_files()
    assert len(files) >= 8, [str(path) for path in files]


def test_education_never_imports_legacy_advertising_architecture() -> None:
    offences: list[str] = []
    for path in _python_files():
        for module in _imported_modules(path):
            if module in ALLOWED:
                continue
            for forbidden in FORBIDDEN_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offences.append(
                        f"{path.relative_to(BACKEND)} imports {module}"
                    )
    assert not offences, "\n".join(offences)


def test_the_advertising_path_does_not_depend_on_education() -> None:
    """
    The dependency points one way. Advertising must keep working untouched, so
    nothing in the campaign services may reach into education.
    """
    offences: list[str] = []
    campaigns = BACKEND / "app" / "services" / "campaigns"
    vision = BACKEND / "app" / "providers" / "vision"
    for path in [*sorted(campaigns.rglob("*.py")), *sorted(vision.rglob("*.py"))]:
        for module in _imported_modules(path):
            if "education" in module:
                offences.append(f"{path.relative_to(BACKEND)} imports {module}")
    assert not offences, "\n".join(offences)
