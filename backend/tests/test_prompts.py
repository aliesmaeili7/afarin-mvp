from app.content.context import CopyContext, PreviousConcept
from app.providers.llm.claims import find_unsupported_claims
from app.providers.llm.openrouter import prompts


def _ctx(**overrides: object) -> CopyContext:
    values: dict = {
        "product_name": "شمع سویا دست‌ریز",
        "description": "رایحه یاس",
        "price_text": None,
        "benefit": None,
        "brand_name": "نورکده",
        "audience": "کسایی که دنبال فضای آروم خونه هستن",
        "objective": "sell_product",
        "style": "minimal",
        "round": 0,
    }
    values.update(overrides)
    return CopyContext(**values)


def test_system_prompt_forbids_invented_business_facts() -> None:
    text = prompts.SYSTEM_PROMPT
    for word in (
        "تخفیف",
        "موجودی محدود",
        "ارسال",
        "واتساپ",
        "لینک بایو",
        "بسته‌بندی",
        "مواد اولیه",
        "ضمانت",
    ):
        assert word in text
    assert "آزادی خلاقانه" in text
    assert "UGC" in text
    assert "hook" in text


def test_system_prompt_asks_for_natural_iranian_persian() -> None:
    text = prompts.SYSTEM_PROMPT
    assert "فارسی معاصر و طبیعی ایرانی" in text
    assert "ترجمهٔ تحت‌اللفظی" in text
    assert "بازاریاب حرفه‌ای نیست" in text


def test_facts_block_lists_missing_price_and_benefit() -> None:
    block = prompts.facts_block(_ctx())
    assert "رایحه یاس" in block
    assert "قیمت" in block
    assert "مزیت اصلی" in block
    assert "نه اشاره کن نه بساز" in block


def test_concepts_prompt_includes_previous_angles() -> None:
    ctx = _ctx(
        round=1,
        previous_concepts=(
            PreviousConcept(
                title_fa="شب آرام",
                description_fa="نور کم و حس خواب",
                visual_direction="مینیمال گرم",
            ),
        ),
    )
    prompt = prompts.concepts_user_prompt(ctx)
    assert "شب آرام" in prompt
    assert "مینیمال گرم" in prompt
    assert "نور کم و حس خواب" in prompt
    assert "بازنویسی" in prompt


def test_promotion_objective_does_not_license_invented_discounts() -> None:
    prompt = prompts.concepts_user_prompt(_ctx(objective="promotion"))
    assert "واژهٔ تخفیف را به کار نبر" in prompt
    assert "حتی اگر هدف کمپین «تبلیغ تخفیف» است" in prompts.SYSTEM_PROMPT


def test_first_round_does_not_invent_previous_ideas() -> None:
    prompt = prompts.concepts_user_prompt(_ctx())
    assert "ایده‌هایی که فروشنده" not in prompt
    prompt = prompts.concepts_user_prompt(_ctx())
    assert "ایده‌هایی که فروشنده" not in prompt


def test_copy_prompt_explains_reel_fields_in_plain_persian() -> None:
    prompt = prompts.copy_user_prompt(_ctx(), headline_fa="یه شب آروم")
    assert "جملهٔ اول که مخاطب را نگه می‌دارد" in prompt
    assert "چه چیزی فیلم گرفته شود" in prompt


def test_rewrite_prompt_forbids_new_facts() -> None:
    prompt = prompts.rewrite_user_prompt(
        _ctx(), intent="stronger_cta", current="سفارش بده", field="cta"
    )
    assert "واقعیت تازه‌ای اضافه نکن" in prompt


def test_flags_invented_discount_scarcity_shipping_and_channels() -> None:
    brief = {
        "product_name": "شمع سویا دست‌ریز",
        "description": "رایحه یاس",
        "brand_name": "نورکده",
    }
    text = (
        "تخفیف ۲۰٪ تا تموم نشده. ارسال رایگان. از واتساپ یا لینک بایو سفارش بده. "
        "موجودی محدود. بسته‌بندی کادویی و ضمانت اصالت."
    )
    categories = {hit.category for hit in find_unsupported_claims(text, brief)}
    assert categories >= {
        "discount",
        "scarcity",
        "shipping",
        "order_channel",
        "packaging",
        "guarantees",
    }


def test_flags_shipping_and_scarcity_seen_in_prior_eval_output() -> None:
    scarf = {
        "product_name": "شال نخی دست‌دوز",
        "description": "پارچه سبک برای بهار",
        "price_text": "۲۴۹ هزار تومان",
        "benefit": "خنک و ضدچروک",
        "brand_name": "نسیم",
        "audience": "خانم‌های ۲۰ تا ۳۵ سال",
    }
    scarf_hits = {
        hit.category
        for hit in find_unsupported_claims(
            "برای سفارش پیام بده؛ سریع برات ارسال می‌کنیم. موجودی محدوده.",
            scarf,
        )
    }
    assert scarf_hits >= {"shipping", "scarcity"}

    tea = {
        "product_name": "چای گل‌گاوزبان",
        "description": "دمنوش آرام‌بخش",
        "price_text": "۸۹ هزار تومان",
        "benefit": "خواب راحت‌تر",
        "brand_name": "گلاب‌جان",
        "audience": "خانواده‌ها",
    }
    tea_hits = {
        hit.category
        for hit in find_unsupported_claims(
            "فرصت تخفیف محدود. تعداد محدود، همین الان بخر.",
            tea,
        )
    }
    assert tea_hits >= {"discount", "scarcity"}


def test_allows_claims_that_are_already_in_the_brief() -> None:
    brief = {
        "product_name": "زعفران ممتاز قائنات",
        "benefit": "عطر قوی و بسته‌بندی هدیه",
        "description": "یک گرمی، مناسب هدیه",
        "price_text": "۳۹۹ هزار تومان",
    }
    text = "زعفران ممتاز قائنات با بسته‌بندی هدیه و عطر قوی. قیمت ۳۹۹ هزار تومان."
    assert find_unsupported_claims(text, brief) == []


def test_generic_instagram_cta_is_not_an_invented_channel() -> None:
    brief = {"product_name": "شمع سویا دست‌ریز", "description": "رایحه یاس"}
    text = "شمع سویا دست‌ریز با رایحه یاس. همین حالا سفارش بده."
    assert find_unsupported_claims(text, brief) == []
