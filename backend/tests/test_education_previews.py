"""
Built-in educational themes stay visual-style-only: palette, material, mood.
They never carry fonts, overlay slots or advertising chrome.
"""

from app.content.education_themes import builtin_themes
from app.services.education.render_spec import (
    AD_COMPOSITION_KEYS,
    build_render_spec,
    is_educational_render_spec,
)

STYLE_KEYS = (
    "palette",
    "illustration_style",
    "mood",
    "lighting",
    "shape_language",
    "decorative_motifs",
)


def test_every_builtin_theme_is_style_memory_only() -> None:
    for theme in builtin_themes():
        for key in STYLE_KEYS:
            assert theme[key], f"{theme['id']} missing {key}"
        assert theme["palette"]["primary"]
        assert "typography" not in theme
        assert "text_treatment" not in theme
        for chrome in AD_COMPOSITION_KEYS:
            assert chrome not in theme


def test_educational_render_spec_is_image_only() -> None:
    spec = build_render_spec(image_path="education/p1/post.jpg")
    assert is_educational_render_spec(spec)
    assert spec["render_mode"] == "educational"
    assert spec["image_path"] == "education/p1/post.jpg"
    for key in AD_COMPOSITION_KEYS:
        assert key not in spec
