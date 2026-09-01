import type { ChatLanguage } from "@/lib/api/chat/types";
import { dictionaries } from "@/lib/i18n/t";

export type ChatActivityPhase =
  | "thinking"
  | "preparing_advertising"
  | "preparing_education"
  | "preparing_image"
  | "generating_image"
  | "finalizing";

export function preparingPhaseFor(
  route: string | null | undefined,
): ChatActivityPhase {
  if (route === "advertising") return "preparing_advertising";
  if (route === "education") return "preparing_education";
  if (route === "general_image") return "preparing_image";
  return "thinking";
}

export function activityCopy(
  phase: string | null | undefined,
  language: ChatLanguage | null | undefined,
  options: { imageCount?: number } = {},
): string {
  const lang = language === "en" ? "en" : "fa";
  const dict = dictionaries[lang].chat.activity;
  if (phase === "generating_image" && options.imageCount === 3) {
    return dict.generatingAds;
  }
  if (phase && phase in dict && phase !== "generatingAds") {
    return dict[phase as keyof typeof dict];
  }
  return dict.thinking;
}
