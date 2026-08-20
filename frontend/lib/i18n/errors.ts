import { ApiError } from "@/lib/api/types";
import type { Locale } from "./types";
import { t, type TranslationKey } from "./t";

const MESSAGE_KEYS: Record<string, TranslationKey> = {
  "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.": "errors.unknown",
  "ارتباط با سرور برقرار نشد. اینترنتت رو چک کن.": "errors.network",
  "این کمپین پیدا نشد.": "errors.campaignNotFound",
  "دسترسی به این کمپین برای شما مجاز نیست.": "errors.campaignForbidden",
  "اسم محصول رو بنویس.": "errors.productNameRequired",
  "حداکثر ۳ عکس می‌تونی اضافه کنی.": "errors.tooManyImages",
  "این عکس پیدا نشد.": "errors.imageNotFound",
  "برای ساخت ایده، هدف و سبک تبلیغ رو انتخاب کن.": "errors.briefIncomplete",
  "این ایده پیدا نشد.": "errors.conceptNotFound",
  "برای ساخت کمپین اول باید وارد بشی.": "errors.signInRequired",
  "اول یکی از ایده‌ها رو انتخاب کن.": "errors.conceptRequired",
  "اول مشخص کن تصویر تبلیغ چطور ساخته بشه.": "errors.visualModeRequired",
  "اول یک سبک تصویری انتخاب کن.": "errors.visualRecipeRequired",
  "این ترکیب سبک و قالب معتبر نیست.": "errors.visualRecipeInvalid",
  "اول یکی از تصویرها رو انتخاب کن.": "errors.candidateRequired",
  "این تصویر پیدا نشد.": "errors.candidateNotFound",
  "برای این کمپین دیگه نمی‌تونی سه نسخه جدید بسازی.": "errors.creativeAttemptsExhausted",
  "عکس محصول برای ساخت تصویر کافی نیست. کادر رو درست کن و دوباره امتحان کن.":
    "errors.inputQualityNeedsFix",
  "عکس محصول برای ساخت تصویر کافی نیست. کادر رو درست کن.": "errors.inputQualityNeedsFixShort",
  "ساخت نسخه جدید برای این حالت از نتیجه کمپین انجام می‌شه.": "errors.accurateRegenOnly",
  "الان تصویرها دارن ساخته می‌شن. کمی صبر کن.": "errors.creativeBusy",
  "این متن پیدا نشد.": "errors.copyNotFound",
  "اسم برند رو بنویس.": "errors.brandNameRequired",
  "این برند پیدا نشد.": "errors.brandNotFound",
  "دسترسی به این برند مجاز نیست.": "errors.brandForbidden",
  "ایمیل معتبر وارد کن.": "errors.invalidEmail",
  "فقط عکس با فرمت JPG، PNG یا WEBP قابل قبوله.": "errors.unsupportedImageType",
  "حجم عکس بیشتر از ۱۲ مگابایته. یه عکس سبک‌تر انتخاب کن.": "errors.imageTooLarge",
  "این فایل یک عکس معتبر نیست.": "errors.invalidImage",
  "ذخیره عکس ناموفق بود.": "errors.uploadFailed",
  "ذخیره عکس روی این مرورگر ممکن نشد.": "errors.uploadFailedBrowser",
  "کادر محصول رو یک مقدار بزرگ‌تر انتخاب کن.": "errors.cropInvalid",
  "کمپینت توی صف ساخته…": "errors.queued",
  "الان داره ساخته می‌شه. کمی صبر کن.": "errors.generationBusy",
  "ساخت این بخش الان ممکن نشد. لطفاً دوباره امتحان کن.": "errors.generationFailed",
  "این تغییر برای این متن ممکن نیست.": "errors.rewriteNotAllowed",
  "حداکثر ۱۰ متن می‌تونی به این تصویر اضافه کنی.": "errors.textLayersLimit",
  "این ویرایش متن معتبر نیست.": "errors.textLayersInvalid",
  "این کمپین قبلاً به یک حساب دیگه منتقل شده.": "errors.alreadyClaimed",
  "رمز باید حداقل ۸ حرف باشه.": "errors.passwordMin",
  "دو رمز یکی نیستن.": "errors.passwordMismatch",
  "ایمیل یا رمز درست نیست.": "errors.invalidCredentials",
  "کد ۶ رقمی رو کامل وارد کن.": "errors.codeIncomplete",
  "این کد منقضی شده. یه کد جدید بگیر.": "errors.codeExpired",
  "کد واردشده درست نیست.": "errors.codeInvalid",
  "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.": "errors.resetLinkInvalid",
  "تعداد تلاش‌ها زیاد بود. چند دقیقه دیگه دوباره امتحان کن.": "errors.rateLimited",
  "این حساب هنوز فعال نشده. از ورود با کد ایمیل استفاده کن.": "errors.emailNotConfirmed",
  "حساب ساخته شد. برای ورود همان ایمیل و رمز رو بزن.": "errors.accountCreatedSignIn",
};

const STAGE_KEYS = {
  planning: "generation.planning",
  visual: "generation.visual",
  captions: "generation.captions",
  story: "generation.story",
  finalizing: "generation.finalizing",
} as const;

export function toDisplayError(error: unknown, locale: Locale): string {
  if (error instanceof ApiError) {
    const key = MESSAGE_KEYS[error.messageFa];
    if (key) return t(locale, key);
    if (locale === "fa") return error.messageFa;
    return t(locale, "errors.unknown");
  }
  if (typeof error === "string") {
    const key = MESSAGE_KEYS[error];
    if (key) return t(locale, key);
    if (locale === "fa") return error;
  }
  return t(locale, "errors.unknown");
}

/** @deprecated Use toDisplayError with the active locale. */
export function toPersianError(error: unknown): string {
  return toDisplayError(error, "fa");
}

export function generationStageMessage(
  locale: Locale,
  stage: string | null | undefined,
  fallback: string | null | undefined,
): string {
  if (stage && stage in STAGE_KEYS) {
    return t(locale, STAGE_KEYS[stage as keyof typeof STAGE_KEYS]);
  }
  if (fallback) return toDisplayError(fallback, locale);
  return t(locale, "generation.preparing");
}
