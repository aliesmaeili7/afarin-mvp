export const LOCALES = ["fa", "en"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "fa";

export function isLocale(value: string | null | undefined): value is Locale {
  return value === "fa" || value === "en";
}

/** Widen Persian `as const` literals so English values can differ while keys stay aligned. */
export type DeepStringify<T> = T extends string
  ? string
  : { [K in keyof T]: DeepStringify<T[K]> };
