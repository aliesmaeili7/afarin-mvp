import type { VisualStyle } from "@/types/domain";

export interface VisualStyleOption {
  value: VisualStyle;
  label_fa: string;
  description_fa: string;
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
    label_fa: "لوکس",
    description_fa: "تیره، خاص و گران‌قیمت",
    preview_css:
      "radial-gradient(120% 90% at 70% 15%, #3b3050 0%, #1b1626 55%, #100c17 100%)",
  },
  {
    value: "minimal",
    label_fa: "مینیمال",
    description_fa: "ساده، تمیز و بدون شلوغی",
    preview_css:
      "linear-gradient(160deg, #f7f5f2 0%, #ecE7e1 60%, #e2dbd3 100%)",
  },
  {
    value: "friendly",
    label_fa: "صمیمی",
    description_fa: "گرم، نزدیک و خودمونی",
    preview_css:
      "radial-gradient(110% 80% at 25% 20%, #ffd9c7 0%, #ffb9a1 45%, #f78d76 100%)",
  },
  {
    value: "bold",
    label_fa: "جسور و رنگی",
    description_fa: "پرانرژی، پررنگ و چشم‌گیر",
    preview_css:
      "linear-gradient(135deg, #7c3aed 0%, #d946ef 45%, #fb7263 100%)",
  },
  {
    value: "persian_traditional",
    label_fa: "سنتی ایرانی",
    description_fa: "اصیل، گرم و ایرانی",
    preview_css:
      "radial-gradient(120% 100% at 50% 0%, #2d5b52 0%, #1d413b 55%, #14302b 100%)",
  },
  {
    value: "modern",
    label_fa: "مدرن",
    description_fa: "امروزی، شیک و حرفه‌ای",
    preview_css:
      "linear-gradient(150deg, #eef2ff 0%, #dbe4ff 45%, #c7d2fe 100%)",
  },
];

export function styleLabel(style: VisualStyle | null): string {
  return VISUAL_STYLES.find((item) => item.value === style)?.label_fa ?? "";
}

export const ALL_STYLE_VALUES: readonly VisualStyle[] = VISUAL_STYLES.map(
  (item) => item.value,
);
