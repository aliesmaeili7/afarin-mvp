"""Persian-quality instructions shared by every OpenRouter completion."""

from app.content.context import CopyContext, PreviousConcept

SYSTEM_PROMPT = """\
تو نویسنده تبلیغات اینستاگرام برای فروشنده‌های کوچک ایرانی هستی.
خروجی را فقط به‌صورت JSON مطابق اسکیما برگردان.

قواعد زبان:
- فارسی معاصر و طبیعی ایرانی بنویس؛ مناسب پیج اینستاگرام یک کسب‌وکار کوچک.
- ترجمهٔ تحت‌اللفظی از انگلیسی ننویس (مثلاً «تجربه را کشف کن» یا «سفر لوکس را آغاز کن»).
- از اصطلاحات اجباری جوان‌پسند، شوخی‌های تصنعی و کلیشه‌های بازاریابی که فروشندهٔ معمولی به کار نمی‌برد پرهیز کن.
- متن باید برای کسی که بازاریاب حرفه‌ای نیست قابل‌فهم باشد.
- نقطه‌گذاری فارسی و نیم‌فاصله را رعایت کن (مثلاً «می‌خوام»، «بسته‌بندی»).
- اسم محصول و برند را دقیقاً همان‌طور که داده شده حفظ کن.
- تا جای ممکن از واژه‌های انگلیسی و لاتین پرهیز کن مگر اینکه بخشی از اسم برند باشد.
- تیترها کوتاه باشند تا روی قالب پست اینستاگرام جا شوند (حدود یک خط).
- متن تبلیغ باید با هدف کمپین، مخاطب و حس بصری هم‌خوان باشد.

حقایق محصول — سخت‌گیرانه:
- فقط از واقعیت‌هایی استفاده کن که در بریف آمده‌اند.
- اگر فیلدی خالی است، آن را نساز و به آن اشاره نکن.
- آزادی خلاقانه برای زاویهٔ کمپین، لحن، حس بصری و سناریوی استوری/ریلز هست؛ این آزادی شامل ساختن واقعیت تجاری یا محصول نیست.
- ادعاهای زیر ممنوع است مگر اینکه عیناً در بریف آمده باشند:
  تخفیف، حراج، درصد، قیمت ویژه
  موجودی محدود، تعداد محدود، فرصت محدود، «تا تموم نشده»
  ارسال، پیک، پست، تحویل
  کانال سفارش مثل لینک بایو، واتساپ، تلفن، وبسایت
  بسته‌بندی
  مواد اولیه و ترکیبات
  مدل، سایز، رنگ یا نسخهٔ دیگر محصول
  تعداد یا حجم محصول
  ضمانت، گارانتی، تضمین، بازگشت وجه
  ویژگی محصول که در بریف نیست
- دعوت به اقدام را کلی نگه دار (مثلاً «سفارش بده») مگر اینکه بریف کانال مشخصی گفته باشد.
- حتی اگر هدف کمپین «تبلیغ تخفیف» است، تا وقتی تخفیف در واقعیت‌های داده‌شده نیامده از واژه‌های تخفیف، حراج، درصد و «قیمت ویژه» استفاده نکن. لحن را فروش‌محور نگه دار، بدون ساختن پیشنهاد.
- از اصطلاحات فیلمبرداری انگلیسی یا معادل‌های قلمبه مثل فلت‌لی، پنکیک، هوک، UGC استفاده نکن.

برای استوری و ریلز:
- به زبان ساده بگو چه چیزی فیلم گرفته شود.
- از اصطلاحات انگلیسی مثل UGC، hook، cut، scene در متن فارسی استفاده نکن.
- اگر لازم شد مفهوم را توضیح بده: مثلاً «جملهٔ اول که مخاطب را نگه می‌دارد» به‌جای hook، «فیلم واقعی از مشتری» به‌جای UGC، «تعویض سریع نما» به‌جای rhythmic cuts.

برای پرامپت تصویر (background_prompt):
- فقط انگلیسی بنویس.
- محیط و نور را توصیف کن، نه خود محصول را جایگزین نکن.
- حتماً عبارت no text را بگذار. هیچ نوشته فارسی یا لاتین روی تصویر نباشد.
"""


OBJECTIVE_FA = {
    "sell_product": "فروش محصول",
    "new_product": "معرفی محصول جدید",
    "promotion": "تبلیغ تخفیف",
    "brand_awareness": "افزایش آگاهی از برند",
}

STYLE_FA = {
    "luxury": "لوکس",
    "minimal": "مینیمال",
    "friendly": "صمیمی",
    "bold": "جسور و رنگی",
    "persian_traditional": "سنتی ایرانی",
    "modern": "مدرن",
}

INTENT_FA = {
    "informal": "متن را خودمونی‌تر و صمیمی‌تر کن",
    "shorter": "متن را کوتاه‌تر کن، معنی را نگه دار",
    "stronger_cta": "دعوت به اقدام را قوی‌تر و مستقیم‌تر کن",
    "new_headline": "یک تیتر فارسی جدید و متفاوت بنویس",
    "more_luxury": "لحن را لوکس‌تر و خاص‌تر کن",
}

_FACT_FIELDS: tuple[tuple[str, str], ...] = (
    ("product_name", "اسم محصول"),
    ("description", "توضیح محصول"),
    ("price_text", "قیمت"),
    ("benefit", "مزیت اصلی"),
    ("brand_name", "اسم برند"),
    ("audience", "مخاطب"),
)


def brief_payload(ctx: CopyContext) -> dict[str, str | int | None]:
    return {
        "product_name": ctx.product_name,
        "description": ctx.description,
        "price_text": ctx.price_text,
        "benefit": ctx.benefit,
        "brand_name": ctx.brand_name,
        "audience": ctx.audience,
        "objective": ctx.objective,
        "objective_fa": OBJECTIVE_FA.get(ctx.objective, ctx.objective),
        "style": ctx.style,
        "style_fa": STYLE_FA.get(ctx.style, ctx.style),
        "round": ctx.round,
        "selected_headline": ctx.selected_headline,
    }


def facts_block(ctx: CopyContext) -> str:
    """Stated brief facts vs empty fields, so the model cannot fill the gaps."""
    known: list[str] = []
    unknown: list[str] = []
    for field, label in _FACT_FIELDS:
        value = getattr(ctx, field)
        if isinstance(value, str) and value.strip():
            known.append(f"- {label}: {value.strip()}")
        else:
            unknown.append(f"- {label}")

    known.append(
        f"- هدف کمپین: {OBJECTIVE_FA.get(ctx.objective, ctx.objective)}"
    )
    known.append(f"- حس بصری: {STYLE_FA.get(ctx.style, ctx.style)}")

    lines = ["واقعیت‌های داده‌شده (فقط همین‌ها):", *known]
    if unknown:
        lines += [
            "",
            "این موارد در بریف نیست؛ نه اشاره کن نه بساز:",
            *unknown,
        ]
    if ctx.objective == "promotion":
        lines += [
            "",
            "هدف «تبلیغ تخفیف» است اما هیچ مقدار یا مهلت تخفیفی در بریف نیست. "
            "واژهٔ تخفیف را به کار نبر؛ لحن را فروش‌محور نگه دار.",
        ]
    return "\n".join(lines)


def concepts_user_prompt(ctx: CopyContext) -> str:
    previous = _previous_block(ctx.previous_concepts)
    extra = ""
    if ctx.round > 0 or ctx.previous_concepts:
        extra = (
            "\nسه زاویهٔ استراتژیک کاملاً متفاوت بساز. بازنویسی یا جابه‌جایی "
            "کلمات ایده‌های قبلی قبول نیست؛ زاویهٔ فروش باید عوض شود."
        )
    return (
        "سه ایده تبلیغاتی کاملاً متمایز بساز. هر ایده title_fa، headline_fa، "
        "description_fa، visual_direction (فارسی: زاویهٔ استراتژیک و حس کمپین) "
        "و background_prompt (انگلیسی، بدون متن روی تصویر) داشته باشد.\n\n"
        f"{facts_block(ctx)}{previous}{extra}"
    )


def copy_user_prompt(ctx: CopyContext, *, headline_fa: str | None = None) -> str:
    headline = headline_fa or ctx.selected_headline or "—"
    return (
        "برای این کمپین یک بسته متن بساز:\n"
        "- سه کپشن با لحن‌های کوتاه / صمیمی / تبلیغاتی\n"
        "- سه ایده استوری کوتاه: هر کدام یک موقعیت قابل فیلم‌گرفتن باشد، "
        "به فارسی ساده، بدون اصطلاح انگلیسی\n"
        "- یک دعوت به اقدام کلی\n"
        "- هشتگ‌ها (با فاصله جدا شوند)\n"
        "- یک زیرتیتر\n"
        "- یک ایده ریلز ۱۰ تا ۱۵ ثانیه‌ای: hook_fa یعنی جملهٔ اول که مخاطب را "
        "نگه می‌دارد؛ scenes_fa سه نما به زبان ساده (چه چیزی فیلم گرفته شود)؛ "
        "cta_fa و متن گوینده. داخل متن فارسی از واژهٔ انگلیسی استفاده نکن.\n\n"
        f"تیتر انتخاب‌شده: {headline}\n"
        f"{facts_block(ctx)}"
    )


def rewrite_user_prompt(
    ctx: CopyContext, *, intent: str, current: str, field: str
) -> str:
    instruction = INTENT_FA.get(intent, intent)
    return (
        f"{instruction}.\n"
        f"نوع متن: {field}\n"
        f"متن فعلی:\n{current}\n\n"
        f"{facts_block(ctx)}\n"
        "واقعیت تازه‌ای اضافه نکن. فقط همان متن بازنویسی‌شده را در text_fa برگردان."
    )


def _previous_block(previous: tuple[PreviousConcept, ...]) -> str:
    if not previous:
        return ""
    lines = [
        "",
        "ایده‌هایی که فروشنده همین الان دیده (تکرار یا بازنویسی نکن):",
    ]
    for index, concept in enumerate(previous, start=1):
        lines.append(
            f"{index}. عنوان: {concept.title_fa}\n"
            f"   زاویهٔ استراتژیک: {concept.visual_direction}\n"
            f"   توضیح: {concept.description_fa}"
        )
    return "\n" + "\n".join(lines)
