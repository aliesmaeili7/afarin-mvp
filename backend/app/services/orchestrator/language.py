"""
Deterministic reply vs artifact language. No LLM.

Reply language is Persian unless the latest user text is clearly English or the
user explicitly asks to be answered in English.

Artifact language is independent. It is only set when the user clearly asks for
on-image / caption / poster text in a language. Otherwise it stays None so the
specialist can honor the untouched natural instruction. Never copy reply_language
onto artifact_language.
"""

from __future__ import annotations

import re
from typing import Literal

ChatLanguage = Literal["fa", "en"]

_ARABIC_SCRIPT = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)

_REPLY_EN = re.compile(
    r"(answer|reply|respond)\s+in\s+english"
    r"|please\s+answer\s+in\s+english"
    r"|به\s*انگلیسی\s*جواب"
    r"|انگلیسی\s*جواب\s*بده",
    re.IGNORECASE,
)
_REPLY_FA = re.compile(
    r"(answer|reply|respond)\s+in\s+(persian|farsi)"
    r"|فارسی\s*جواب\s*بده"
    r"|به\s*فارسی\s*جواب",
    re.IGNORECASE,
)

_ARTIFACT_EN = re.compile(
    r"متن(?:ش|ش)?\s*انگلیسی"
    r"|کپشن\s*انگلیسی"
    r"|caption\s+in\s+english"
    r"|english\s+(caption|text|copy|headline)"
    r"|on[- ]image\s+text\s+in\s+english"
    r"|پوستر\s*.{0,24}انگلیسی"
    r"|انگلیسی\s*باشه",
    re.IGNORECASE,
)
_ARTIFACT_FA = re.compile(
    r"متن(?:ش|ش)?\s*فارسی"
    r"|کپشن\s*فارسی"
    r"|caption\s+in\s+(persian|farsi)"
    r"|persian\s+(caption|text|copy)"
    r"|پوستر\s*.{0,24}فارسی"
    r"|فارسی\s*باشه",
    re.IGNORECASE,
)

_THREE_IMAGES = re.compile(
    r"سه\s*تا(?:\s+تبلیغ|\s+نسخه|\s+تصویر)?"
    r"|سه\s*نسخه"
    r"|\bthree\s+(ads?|versions?|images?)\b"
    r"|\b3\s+(ads?|versions?|images?)\b",
    re.IGNORECASE,
)


def reply_language(text: str) -> ChatLanguage:
    latest = text or ""
    if _REPLY_EN.search(latest):
        return "en"
    if _REPLY_FA.search(latest):
        return "fa"
    return "en" if _primarily_english(latest) else "fa"


def artifact_language(text: str) -> ChatLanguage | None:
    """Obvious on-image / caption language only. None means let the skill infer."""
    latest = text or ""
    if _ARTIFACT_EN.search(latest):
        return "en"
    if _ARTIFACT_FA.search(latest):
        return "fa"
    return None


def requested_image_count(text: str) -> int:
    return 3 if _THREE_IMAGES.search(text or "") else 1


def _primarily_english(text: str) -> bool:
    letters = _LETTER.findall(text)
    if not letters:
        return False
    arabic = sum(1 for char in letters if _ARABIC_SCRIPT.search(char))
    return (arabic / len(letters)) < 0.15
