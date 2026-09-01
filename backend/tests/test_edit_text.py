"""Deterministic Phase D helpers. No provider calls."""

from app.services.orchestrator.edit_text import (
    is_caption_request,
    is_deictic_latest,
    is_edit_request,
    is_regenerate_request,
    parse_target_aspect,
    quoted_strings,
    should_apply_theme,
    wants_rendered_ad_as_product,
)


def test_parse_target_aspect() -> None:
    assert parse_target_aspect("همین رو استوری کن") == "9:16"
    assert parse_target_aspect("مربعش کن") == "1:1"
    assert parse_target_aspect("برای فید 4:5 کن") == "4:5"
    assert parse_target_aspect("make this vertical") == "9:16"
    assert parse_target_aspect("روشن‌ترش کن") is None


def test_quoted_strings_preserved() -> None:
    assert quoted_strings("تیتر رو بکن «ماموریت کسرها»") == ("ماموریت کسرها",)
    assert quoted_strings('change the title to "Hello"') == ("Hello",)


def test_edit_vs_regenerate_vs_caption() -> None:
    assert is_edit_request("روشن‌ترش کن")
    assert is_edit_request("make this brighter")
    assert is_regenerate_request("یکی دیگه شبیه همین بساز")
    assert is_caption_request("یه کپشن براش بده")
    assert is_deictic_latest("عکس قبلی")
    assert not is_edit_request("یه کپشن براش بده")


def test_theme_and_rendered_product_flags() -> None:
    assert should_apply_theme("همین رو با تم خمیری من بساز")
    assert not should_apply_theme("فقط روشن‌ترش کن")
    assert wants_rendered_ad_as_product(
        "از همین تبلیغ به عنوان عکس محصول استفاده کن"
    )
    assert not wants_rendered_ad_as_product("یکی دیگه تبلیغ بساز")
