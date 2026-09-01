"""Deterministic edit helpers. No extra LLM."""

from __future__ import annotations

import re
from typing import Any

_EDIT = re.compile(
    r"روشن‌?تر|تاریک‌?تر|پس[\s‌-]*زمینه|بک[\s‌-]*گراند|حذف کن|عوض کن|تیتر|"
    r"مینیمال‌?تر|استوری(?:ش|‌ش)?\s*کن|مربعش|عمودی|"
    r"make this brighter|brighter|darker|remove the|change the (title|text|background)|"
    r"make this vertical|make it square|reframe",
    re.IGNORECASE,
)
_REGENERATE = re.compile(
    r"یکی\s+دیگه|یه\s+نسخه\s+دیگه|نسخه\s+دیگه|سه\s+تا\s+(?:تبلیغ|نسخه)|"
    r"\banother (?:one|version)\b|\bone more\b|\btry a different\b|"
    r"\bgive me 3\b|alternatives",
    re.IGNORECASE,
)
_CAPTION = re.compile(r"کپشن|\bcaption\b", re.IGNORECASE)
_DEICTIC_LATEST = re.compile(
    r"عکس\s+قبلی|تصویر\s+قبلی|همینه?|همونه?|آخری|"
    r"\bthis one\b|\bthe previous image\b|\bthe last image\b|"
    r"\bthe previous one\b|\bthat image\b",
    re.IGNORECASE,
)
_STORY = re.compile(
    r"استوری|عمودی|9\s*[:x×]\s*16|\b9:16\b|\bstory\b|\bvertical\b",
    re.IGNORECASE,
)
_SQUARE = re.compile(r"مربع|1\s*[:x×]\s*1|\b1:1\b|\bsquare\b", re.IGNORECASE)
_FEED = re.compile(r"فید|4\s*[:x×]\s*5|\b4:5\b|\bfeed\b", re.IGNORECASE)
_THEME = re.compile(r"\bتم\b|\btheme\b|با\s+همون\s+تم", re.IGNORECASE)
_RENDERED_AS_PRODUCT = re.compile(
    r"به\s+عنوان\s+(?:عکس\s+)?محصول|"
    r"as the product|"
    r"use this (?:ad|image|photo) as (?:the )?product|"
    r"خودِ?\s*این\s+تبلیغ",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"[«\"“]([^»\"”]+)[»\"”]")


def is_edit_request(text: str) -> bool:
    return bool(_EDIT.search(text or ""))


def is_regenerate_request(text: str) -> bool:
    return bool(_REGENERATE.search(text or ""))


def is_caption_request(text: str) -> bool:
    return bool(_CAPTION.search(text or ""))


def is_deictic_latest(text: str) -> bool:
    return bool(_DEICTIC_LATEST.search(text or ""))


def wants_rendered_ad_as_product(text: str) -> bool:
    return bool(_RENDERED_AS_PRODUCT.search(text or ""))


def should_apply_theme(text: str) -> bool:
    return bool(_THEME.search(text or ""))


def parse_target_aspect(text: str) -> str | None:
    raw = text or ""
    if _STORY.search(raw):
        return "9:16"
    if _SQUARE.search(raw):
        return "1:1"
    if _FEED.search(raw):
        return "4:5"
    return None


def quoted_strings(text: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in _QUOTED.findall(text or "") if item.strip())


def theme_line(text: str, theme: dict[str, Any] | None) -> str | None:
    if not theme or not should_apply_theme(text):
        return None
    name = theme.get("name")
    if isinstance(name, str) and name.strip():
        return f"Apply the active theme named {name.strip()}."
    return "Apply the conversation's active theme."
