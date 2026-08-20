"""
User-facing Persian strings.

Copied verbatim from the Phase 1 mock (frontend/lib/api/mock/mockApi.ts and
lib/storage/imageStore.ts) so that swapping MockApi for HttpApi cannot change a
single word the user reads. Raw provider or database errors never reach here
(spec §27).
"""

CAMPAIGN_NOT_FOUND = "این کمپین پیدا نشد."
CAMPAIGN_FORBIDDEN = "دسترسی به این کمپین برای شما مجاز نیست."
PRODUCT_NAME_REQUIRED = "اسم محصول رو بنویس."
TOO_MANY_IMAGES = "حداکثر ۳ عکس می‌تونی اضافه کنی."
IMAGE_NOT_FOUND = "این عکس پیدا نشد."
BRIEF_INCOMPLETE = "برای ساخت ایده، هدف و سبک تبلیغ رو انتخاب کن."
CONCEPT_NOT_FOUND = "این ایده پیدا نشد."
SIGN_IN_REQUIRED = "برای ساخت کمپین اول باید وارد بشی."
CONCEPT_REQUIRED = "اول یکی از ایده‌ها رو انتخاب کن."
VISUAL_MODE_REQUIRED = "اول مشخص کن تصویر تبلیغ چطور ساخته بشه."
VISUAL_RECIPE_REQUIRED = "اول یک سبک تصویری انتخاب کن."
VISUAL_RECIPE_INVALID = "این ترکیب سبک و قالب معتبر نیست."
CANDIDATE_REQUIRED = "اول یکی از تصویرها رو انتخاب کن."
CANDIDATE_NOT_FOUND = "این تصویر پیدا نشد."
CREATIVE_ATTEMPTS_EXHAUSTED = (
    "برای این کمپین دیگه نمی‌تونی سه نسخه جدید بسازی."
)
INPUT_QUALITY_NEEDS_FIX = (
    "عکس محصول برای ساخت تصویر کافی نیست. کادر رو درست کن و دوباره امتحان کن."
)
ACCURATE_REGEN_ONLY = "ساخت نسخه جدید برای این حالت از نتیجه کمپین انجام می‌شه."
CREATIVE_BUSY = "الان تصویرها دارن ساخته می‌شن. کمی صبر کن."
COPY_NOT_FOUND = "این متن پیدا نشد."
ASSET_NOT_FOUND = "این تصویر پیدا نشد."
BRAND_NAME_REQUIRED = "اسم برند رو بنویس."
BRAND_NOT_FOUND = "این برند پیدا نشد."
BRAND_FORBIDDEN = "دسترسی به این برند مجاز نیست."
INVALID_EMAIL = "ایمیل معتبر وارد کن."

UNSUPPORTED_IMAGE_TYPE = "فقط عکس با فرمت JPG، PNG یا WEBP قابل قبوله."
IMAGE_TOO_LARGE = "حجم عکس بیشتر از ۱۲ مگابایته. یه عکس سبک‌تر انتخاب کن."
INVALID_IMAGE = "این فایل یک عکس معتبر نیست."
UPLOAD_FAILED = "ذخیره عکس ناموفق بود."
CROP_INVALID = "کادر محصول رو یک مقدار بزرگ‌تر انتخاب کن."

QUEUED = "کمپینت توی صف ساخته…"
GENERATION_BUSY = "الان داره ساخته می‌شه. کمی صبر کن."
GENERATION_FAILED = "ساخت این بخش الان ممکن نشد. لطفاً دوباره امتحان کن."
REWRITE_NOT_ALLOWED = "این تغییر برای این متن ممکن نیست."
TEXT_LAYERS_LIMIT = "حداکثر ۱۰ متن می‌تونی به این تصویر اضافه کنی."
TEXT_LAYERS_INVALID = "این ویرایش متن معتبر نیست."
GENERIC = "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن."

ALREADY_CLAIMED = "این کمپین قبلاً به یک حساب دیگه منتقل شده."
