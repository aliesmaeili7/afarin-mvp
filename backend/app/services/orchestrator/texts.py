"""User-visible chat copy. Deterministic; never model names or skill ids."""

from __future__ import annotations

from app.services.orchestrator.language import ChatLanguage
from app.services.orchestrator.schema import Route

ACK = {
    "advertising": {
        "fa": "حتما، یه تبلیغ برات می‌سازم.",
        "en": "Sure — I’ll make an ad for you.",
    },
    "education": {
        "fa": "باشه، یه پست آموزشی تمیز و جذاب برات می‌سازم.",
        "en": "Got it — I’ll make a clean teaching post.",
    },
    "general_image": {
        "fa": "باشه، تصویرش رو می‌سازم.",
        "en": "Got it — I’ll make that image.",
    },
}

CLARIFY_ADS = {
    "fa": "یه عکس از محصول بفرست تا بتونم تبلیغش رو بسازم.",
    "en": "Send a product photo and I’ll make the ad.",
}
CLARIFY_IMAGE = {
    "fa": "چی رو برات تصویر کنم؟ یه موضوع کوتاه بگو.",
    "en": "What should I draw? Give me a short subject.",
}
UNSUPPORTED = {
    "fa": "این قابلیت هنوز فعال نیست. می‌تونم برات تبلیغ، پست آموزشی یا تصویر بسازم.",
    "en": "That isn’t available yet. I can make ads, teaching posts, or images.",
}
TRY_AGAIN = {
    "fa": "یه لحظه نتونستم درست بفهمم چی می‌خوای. دوباره بگو؟",
    "en": "I couldn’t quite tell what you needed. Try saying it again?",
}
GENERIC_CHAT = {
    "fa": "بگو چی لازم داری؛ می‌تونم تبلیغ، پست آموزشی یا تصویر برات بسازم.",
    "en": "Tell me what you need — I can make an ad, a teaching post, or an image.",
}


def ack_for(route: Route, language: ChatLanguage) -> str:
    row = ACK.get(route)
    if not row:
        return ""
    return row[language]


def fallback_for(route: Route, language: ChatLanguage) -> str:
    if route == "unsupported":
        return UNSUPPORTED[language]
    if route == "clarify":
        return CLARIFY_IMAGE[language]
    if route == "general_chat":
        return GENERIC_CHAT[language]
    return TRY_AGAIN[language]
