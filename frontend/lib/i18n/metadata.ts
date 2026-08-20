import type { Metadata } from "next";
import { cookies } from "next/headers";
import { LOCALE_COOKIE, parseLocale } from "./cookies";
import { t, type TranslationKey } from "./t";

export async function readRequestLocale() {
  const store = await cookies();
  return parseLocale(store.get(LOCALE_COOKIE)?.value);
}

export async function localeMetadata(titleKey: TranslationKey): Promise<Metadata> {
  const locale = await readRequestLocale();
  return { title: t(locale, titleKey) };
}
