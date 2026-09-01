"""
Deterministic Educational Agent for tests, CI and offline development.

It is not a language model, but it obeys the same contract the real agent is
held to: the output language follows the request, `final_prompt` stays inside
the character budget, names the square format, and carries any wording the
teacher already wrote so the image model can paint it.
"""

from __future__ import annotations

import json
import re

from app.providers.education.base import (
    EducationalAgentContext,
    EducationalPostResult,
    EducationalTheme,
)
from app.providers.education.prompts import (
    FINAL_PROMPT_MAX_CHARS,
    educational_agent_system,
    educational_user_prompt,
)
from app.providers.vision.base import LlmCallTrace

_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")

_DEFAULT_THEME = {
    "name_suggestion": "تم آموزشی آفرین",
    "primary_colors": ("#7c3aed", "#22d3ee"),
    "secondary_colors": ("#fde047",),
    "illustration_style": "friendly 3D clay render with matte surfaces",
    "mood": "playful, warm, inviting for a classroom",
    "lighting": "soft wraparound studio light with gentle ambient occlusion",
    "shape_language": "rounded blobs and pills, no sharp corners",
    "decorative_motifs": ("stars", "dotted path", "floating cubes"),
}

_FA = {
    "name": "تم آموزشی آفرین",
    "prompt": (
        "یک پوستر آموزشی مربعی 1:1 برای اینستاگرام بساز. "
        "صحنه روشن و دوستانه است و شخصیت اصلی درس در مرکز تصویر دیده می‌شود. "
        "سبک تصویر رندر سه‌بعدی خمیری با سطوح مات و رنگ‌های بنفش و فیروزه‌ای است. "
        "نور نرم و یکنواخت است. دکمه فراخوان، نشان امتیاز، برچسب قیمت یا برند نکش."
    ),
}

_EN = {
    "name": "Afarin Educational Theme",
    "prompt": (
        "Create a finished square 1:1 Instagram educational poster. "
        "A friendly classroom scene fills the frame with the lesson's main "
        "subject in the centre. Render it as 3D clay with matte surfaces in "
        "purple and teal, under soft even lighting. Do not add CTA buttons, "
        "score badges, price tags or brand chips."
    ),
}


def stub_educational_result(
    context: EducationalAgentContext,
    *,
    correction: str | None = None,
) -> EducationalPostResult:
    prompt = context.user_prompt.strip()
    language = "fa" if _PERSIAN_RE.search(prompt) else "en"
    theme = _theme_for(context, language=language)
    return EducationalPostResult(
        language=language,
        final_prompt=_final_prompt(prompt, language=language, theme=theme),
        theme=theme,
        theme_style_notes=_style_notes(theme, language=language),
        safety_notes=None,
        llm_trace=LlmCallTrace(
            name="educational_agent",
            model="stub",
            system=educational_agent_system(),
            user=educational_user_prompt(context, correction=correction),
            output=json.dumps(
                {
                    "language": language,
                    "theme_selected": bool(context.selected_theme),
                    "correction": bool(correction),
                },
                ensure_ascii=False,
            ),
        ),
    )


def _final_prompt(
    prompt: str, *, language: str, theme: EducationalTheme
) -> str:
    """
    A finished-poster prompt. Any wording the teacher already wrote is carried
    in so the image model can paint it; there is no reserved overlay band.
    """
    words = _FA if language == "fa" else _EN
    snippet = " ".join(prompt.split())[:180]
    if language == "fa":
        body = (
            f"{words['prompt']} "
            f"سبک: {theme.illustration_style}. حال‌وهوا: {theme.mood}. "
            f"نور: {theme.lighting}. "
            f"اگر درخواست معلم متن مشخصی دارد، همان را خوانا در پوستر بنویس: "
            f"{snippet}"
        )
    else:
        body = (
            f"{words['prompt']} "
            f"Look: {theme.illustration_style}. Mood: {theme.mood}. "
            f"Lighting: {theme.lighting}. "
            f"If the teacher already gave exact wording, paint it clearly on "
            f"the poster: {snippet}"
        )
    return body[:FINAL_PROMPT_MAX_CHARS]


def _style_notes(theme: EducationalTheme, *, language: str) -> str:
    if language == "fa":
        return f"{theme.illustration_style}؛ {theme.mood}"
    return f"{theme.illustration_style}; {theme.mood}"


def _theme_for(
    context: EducationalAgentContext, *, language: str
) -> EducationalTheme:
    """
    Echoes a selected theme so consistency is visible in tests, otherwise
    returns the built-in default design.
    """
    selected = context.selected_theme or {}
    palette = selected.get("palette") or {}
    primary = tuple(palette.get("primary") or ()) or _DEFAULT_THEME[
        "primary_colors"
    ]
    secondary = tuple(palette.get("secondary") or ()) or _DEFAULT_THEME[
        "secondary_colors"
    ]
    name = selected.get("name") or _DEFAULT_THEME["name_suggestion"]
    if not context.selected_theme and language == "en":
        name = _EN["name"]
    return EducationalTheme(
        name_suggestion=str(name),
        primary_colors=tuple(str(color) for color in primary),
        secondary_colors=tuple(str(color) for color in secondary),
        illustration_style=str(
            selected.get("illustration_style")
            or _DEFAULT_THEME["illustration_style"]
        ),
        mood=str(selected.get("mood") or _DEFAULT_THEME["mood"]),
        lighting=str(selected.get("lighting") or _DEFAULT_THEME["lighting"]),
        shape_language=str(
            selected.get("shape_language") or _DEFAULT_THEME["shape_language"]
        ),
        decorative_motifs=tuple(
            str(row)
            for row in (
                selected.get("decorative_motifs")
                or _DEFAULT_THEME["decorative_motifs"]
            )
        ),
    )


class StubEducationalAgent:
    name = "stub"
    model: str | None = None

    async def create_post(
        self,
        context: EducationalAgentContext,
        *,
        correction: str | None = None,
    ) -> EducationalPostResult:
        return stub_educational_result(context, correction=correction)
