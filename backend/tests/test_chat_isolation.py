"""Chat modules must not grow advertising/education generation imports."""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

CHAT_MODULES = (
    BACKEND / "app" / "services" / "chat",
    BACKEND / "app" / "api" / "v1" / "chat.py",
    BACKEND / "app" / "schemas" / "chat.py",
    BACKEND / "app" / "db" / "models" / "chat.py",
)

FORBIDDEN_IMPORTS = (
    "app.providers.vision.openrouter",
    "app.providers.vision.stub",
    "app.providers.vision.prompts",
    "app.providers.vision.architect_validate",
    "app.providers.vision.creative_validate",
    "app.providers.image",
    "app.providers.education",
    "app.providers.llm",
    "app.services.education.generate",
    "app.services.education.core",
    "app.services.campaigns.planner",
    "app.services.campaigns.creative",
    "app.services.campaigns.creative_core",
    "app.services.campaigns.visuals",
    "app.services.campaigns.recipes",
    "app.services.campaigns.materialize",
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for target in CHAT_MODULES:
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


def test_chat_modules_exist() -> None:
    files = _python_files()
    assert len(files) >= 4, [str(path) for path in files]


def test_chat_persistence_does_not_import_generation() -> None:
    offences: list[str] = []
    for path in _python_files():
        for module in _imported_modules(path):
            for forbidden in FORBIDDEN_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offences.append(
                        f"{path.relative_to(BACKEND)} imports {module}"
                    )
    assert not offences, "\n".join(offences)
