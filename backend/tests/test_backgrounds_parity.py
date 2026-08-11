"""
Guards the one thing the split between backend and frontend can silently break.

The backend chooses a background_id; the frontend owns the CSS that paints it.
If either side gains or renames one, generated ads fall back to a default
gradient and nobody notices until a seller sees the wrong ad. This test parses
the TypeScript source directly rather than a copy, so drift fails the build.
"""

import re
from pathlib import Path

from app.content.backgrounds import BACKGROUNDS_BY_STYLE, all_background_ids

TS_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "lib"
    / "content"
    / "backgrounds.ts"
)

_ENTRY = re.compile(r'id:\s*"(?P<id>[^"]+)",\s*\n\s*style:\s*"(?P<style>[^"]+)"')


def _parse_typescript() -> dict[str, set[str]]:
    source = TS_SOURCE.read_text(encoding="utf-8")
    by_style: dict[str, set[str]] = {}
    for match in _ENTRY.finditer(source):
        by_style.setdefault(match.group("style"), set()).add(match.group("id"))
    return by_style


def test_typescript_source_is_parseable() -> None:
    assert TS_SOURCE.exists()
    assert _parse_typescript(), "no background definitions found; the regex has rotted"


def test_every_style_matches_the_frontend() -> None:
    frontend = _parse_typescript()
    backend = {style: set(ids) for style, ids in BACKGROUNDS_BY_STYLE.items()}
    assert backend == frontend


def test_no_background_id_is_orphaned() -> None:
    frontend_ids = {
        background for ids in _parse_typescript().values() for background in ids
    }
    assert all_background_ids() == frontend_ids
