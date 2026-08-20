import type { Locale } from "@/lib/i18n/types";
import { t, type TranslationKey } from "@/lib/i18n/t";
import type { VisualStyle } from "@/types/domain";

export interface VisualStyleOption {
  value: VisualStyle;
  /**
   * Small colour swatch used where a full ad preview would be overkill, such as
   * the brand kit's default-style picker. The style step renders a real
   * `AdCanvas` preview instead.
   */
  preview_css: string;
}

/** Spec §9 — visual direction cards, never a dropdown. */
export const VISUAL_STYLES: readonly VisualStyleOption[] = [
  {
    value: "luxury",
    preview_css:
      "radial-gradient(120% 90% at 70% 15%, #3b3050 0%, #1b1626 55%, #100c17 100%)",
  },
  {
    value: "minimal",
    preview_css:
      "linear-gradient(160deg, #f7f5f2 0%, #ecE7e1 60%, #e2dbd3 100%)",
  },
  {
    value: "friendly",
    preview_css:
      "radial-gradient(110% 80% at 25% 20%, #ffd9c7 0%, #ffb9a1 45%, #f78d76 100%)",
  },
  {
    value: "bold",
    preview_css:
      "linear-gradient(135deg, #7c3aed 0%, #d946ef 45%, #fb7263 100%)",
  },
  {
    value: "persian_traditional",
    preview_css:
      "radial-gradient(120% 100% at 50% 0%, #2d5b52 0%, #1d413b 55%, #14302b 100%)",
  },
  {
    value: "modern",
    preview_css:
      "linear-gradient(150deg, #eef2ff 0%, #dbe4ff 45%, #c7d2fe 100%)",
  },
];

export function styleLabel(style: VisualStyle | null, locale: Locale = "fa"): string {
  if (!style) return "";
  return t(locale, `campaign.style.${style}.label` as TranslationKey);
}

export const ALL_STYLE_VALUES: readonly VisualStyle[] = VISUAL_STYLES.map(
  (item) => item.value,
);
