const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];

/** Digits are displayed Persian; stored values stay Latin (spec §28). */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

export function toLatinDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)));
}

/**
 * Normalises Arabic code points that Persian keyboards frequently produce,
 * while leaving the ZWNJ (نیم‌فاصله) untouched.
 */
export function normalizePersian(value: string): string {
  return value
    .replace(/\u064A/g, "\u06CC") // ي -> ی
    .replace(/\u0643/g, "\u06A9") // ك -> ک
    .replace(/\u06C0/g, "\u0647\u200C") // ۀ -> ه + ZWNJ
    .replace(/\u0640/g, "") // strip tatweel
    .replace(/[\u200B\u200D\u200E\u200F]/g, "") // strip stray bidi marks, keep ZWNJ
    .replace(/[ \t]{2,}/g, " ");
}

/** Formats a raw number as a Persian price string, e.g. ۳۹۹٬۰۰۰ تومان. */
export function formatToman(amount: number): string {
  const grouped = new Intl.NumberFormat("fa-IR").format(amount);
  return `${grouped} تومان`;
}

const PERSIAN_MONTHS = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
];

/** Jalali calendar date, e.g. ۲۳ مرداد ۱۴۰۴. */
export function formatJalaliDate(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";

  const parts = new Intl.DateTimeFormat("en-u-ca-persian", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    timeZone: "UTC",
  }).formatToParts(date);

  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  const month = PERSIAN_MONTHS[Number(get("month")) - 1] ?? "";
  const year = get("year").replace(/[^0-9]/g, "");

  return `${toPersianDigits(get("day"))} ${month} ${toPersianDigits(year)}`;
}

/** Relative day label used on dashboard cards. */
export function formatRelativeDay(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";

  const dayMs = 24 * 60 * 60 * 1000;
  const days = Math.floor((Date.now() - date.getTime()) / dayMs);

  if (days <= 0) return "امروز";
  if (days === 1) return "دیروز";
  if (days < 7) return `${toPersianDigits(days)} روز پیش`;
  return formatJalaliDate(isoDate);
}
