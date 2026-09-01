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
    "image_edit": {
        "fa": "باشه، تغییرات رو روی تصویر اعمال می‌کنم.",
        "en": "Got it — I’ll apply that to the image.",
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
CLARIFY_EDIT = {
    "fa": "کدوم تصویر رو می‌خوای تغییر بدم؟ یه عکس بفرست یا یکی از تصاویر گفتگو رو به‌عنوان مرجع انتخاب کن.",
    "en": "Which image should I change? Send a photo or choose one from this chat as a reference.",
}
CLARIFY_EDIT_AMBIGUOUS = {
    "fa": "کدوم تصویر رو می‌گی؟ اگه روی همون عکس «استفاده به‌عنوان مرجع» بزنی، دقیقاً همونو تغییر می‌دم.",
    "en": "Which image do you mean? Tap Use as reference on that photo and I’ll edit exactly that one.",
}
UNSUPPORTED = {
    "fa": "این قابلیت هنوز فعال نیست. می‌تونم برات تبلیغ، پست آموزشی یا تصویر بسازم.",
    "en": "That isn’t available yet. I can make ads, teaching posts, or images.",
}
TRY_AGAIN = {
    "fa": "یه لحظه نتونستم درست بفهمم چی می‌خوای. دوباره بگو؟",
    "en": "I couldn’t quite tell what you needed. Try saying it again?",
}
EDIT_FAILED = {
    "fa": "نتونستم تغییرات رو روی تصویر اعمال کنم. دوباره امتحان کنم؟",
    "en": "I couldn't apply those changes to the image. Want me to try again?",
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
