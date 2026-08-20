"""Detect product/business claims that are not grounded in the campaign brief."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

# ZWNJ and extra spaces so «بسته‌بندی» matches «بسته بندی».
_ZWNJ = re.compile(r"[\u200c\u200d]")
_SPACES = re.compile(r"\s+")

BRIEF_FIELDS = (
    "product_name",
    "description",
    "price_text",
    "benefit",
    "brand_name",
    "audience",
)


@dataclass(frozen=True, slots=True)
class ClaimHit:
    category: str
    snippet: str


# Each pattern is a claim family. If the same pattern also matches the brief,
# the claim is treated as grounded.
_PATTERNS: dict[str, tuple[str, ...]] = {
    "discount": (
        r"تخفیف",
        r"حراج",
        r"٪",
        r"%",
        r"درصد",
        r"آفر",
        r"قیمت\s*ویژه",
        r"off\b",
    ),
    "scarcity": (
        r"موجودی\s*محدود",
        r"تعداد\s*محدود",
        r"فرصت\s*محدود",
        r"تا\s*تموم\s*نشده",
        r"فقط\s*امروز",
        r"آخرین\s*(فرص|عدد|دونه)",
        r"عجله\s*کن",
        r"در\s*حال\s*اتمام",
    ),
    "shipping": (
        r"ارسال",
        r"پیک",
        r"پست\s*می‌",
        r"تحویل\s*درب",
        r"تحویل\s*فوری",
    ),
    "order_channel": (
        r"واتس‌?\s*اپ",
        r"whats?app",
        r"لینک\s*(این\s*)?بایو",
        r"link\s*in\s*bio",
        r"وبسایت",
        r"وب\s*سایت",
        r"سایت\s*ما",
        r"شماره\s*تماس",
        r"تماس\s*بگیر",
        r"زنگ\s*بزن",
    ),
    "packaging": (r"بسته‌?\s*بندی",),
    "ingredients": (
        r"روغن",
        r"اسانس",
        r"مواد\s*اولیه",
        r"ترکیبات",
        r"حاوی",
    ),
    "variants": (
        r"رنگبندی",
        r"سایزبندی",
        r"در\s*سه\s*مدل",
        r"نسخه\s*جدید",
    ),
    "counts": (
        r"بسته\s*\d+",
        r"\d+\s*عددی",
        r"پک\s*\d+",
    ),
    "guarantees": (
        r"ضمانت",
        r"گارانتی",
        r"تضمین",
        r"بازگشت\s*وجه",
    ),
    "features": (
        r"کاملاً\s*طبیعی",
        r"ارگانیک",
        r"صادراتی",
        r"ضدحساسیت",
        r"۱۰۰\s*درصد",
    ),
}

COMPILED: dict[str, tuple[re.Pattern[str], ...]] = {
    category: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for category, patterns in _PATTERNS.items()
}


def normalize(text: str) -> str:
    return _SPACES.sub(" ", _ZWNJ.sub("", text)).strip()


def brief_text(brief: Mapping[str, object]) -> str:
    parts: list[str] = []
    for field in BRIEF_FIELDS:
        value = brief.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return normalize(" ".join(parts))


def find_unsupported_claims(text: str, brief: Mapping[str, object]) -> list[ClaimHit]:
    """Return invented-fact hits; phrases also present in the brief are skipped."""
    blob = brief_text(brief)
    haystack = normalize(text)
    hits: list[ClaimHit] = []
    seen: set[tuple[str, str]] = set()
    for category, patterns in COMPILED.items():
        for pattern in patterns:
            if blob and pattern.search(blob):
                continue
            for match in pattern.finditer(haystack):
                snippet = match.group(0)
                key = (category, snippet)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(ClaimHit(category=category, snippet=snippet))
    return hits
