"""Phase C language helper. No HTTP, no models."""

from app.services.orchestrator.language import (
    artifact_language,
    reply_language,
    requested_image_count,
)


def test_reply_language_matrix() -> None:
    assert reply_language("یه پست آموزشی بساز") == "fa"
    assert reply_language("یه minimal ad بساز") == "fa"
    assert reply_language("برای Instagram کپشن بده") == "fa"
    assert reply_language("Make an ad for this.") == "en"
    assert reply_language("Please answer in English: برای این کپشن بده") == "en"
    assert reply_language("فارسی جواب بده: Make an ad") == "fa"


def test_artifact_language_is_independent_of_reply() -> None:
    text = "یه پوستر بساز ولی متنش انگلیسی باشه"
    assert reply_language(text) == "fa"
    assert artifact_language(text) == "en"
    assert artifact_language("یه پست آموزشی بساز") is None
    assert artifact_language("Make an ad for this.") is None
    assert artifact_language("کپشن انگلیسی باشه") == "en"


def test_requested_image_count() -> None:
    assert requested_image_count("یه تبلیغ بساز") == 1
    assert requested_image_count("سه تا تبلیغ بساز") == 3
    assert requested_image_count("three versions please") == 3
