import type { Locale } from "@/lib/i18n/types";
import { t } from "@/lib/i18n/t";
import {
  formatJalaliDate,
  formatRelativeDay as formatJalaliRelative,
  toPersianDigits,
} from "./persian";

export function formatDigits(value: string | number, locale: Locale): string {
  return locale === "fa" ? toPersianDigits(value) : String(value);
}

export function formatPercent(percent: number, locale: Locale): string {
  return locale === "fa" ? `٪${toPersianDigits(percent)}` : `${percent}%`;
}

export function formatRelativeDay(isoDate: string, locale: Locale): string {
  if (locale === "fa") return formatJalaliRelative(isoDate);

  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";

  const dayMs = 24 * 60 * 60 * 1000;
  const days = Math.floor((Date.now() - date.getTime()) / dayMs);

  if (days <= 0) return t("en", "dates.today");
  if (days === 1) return t("en", "dates.yesterday");
  if (days < 7) return t("en", "dates.daysAgo", { n: days });
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export { formatJalaliDate, toPersianDigits };
