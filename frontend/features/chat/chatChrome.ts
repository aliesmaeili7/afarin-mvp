import type { Locale } from "@/lib/i18n/types";
import { localeDir } from "@/lib/i18n/cookies";

export type ChatMenuSurface = "sheet" | "popover";

export function chatChromeDir(locale: Locale): "rtl" | "ltr" {
  return localeDir(locale);
}

export function chatMenuSurface(mobile: boolean): ChatMenuSurface {
  return mobile ? "sheet" : "popover";
}
