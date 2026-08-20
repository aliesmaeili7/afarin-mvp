/**
 * Curated OFL Persian-capable faces for ad typography.
 *
 * The product UI stays on Vazirmatn. These families apply only inside AdCanvas
 * so sellers can change the look of a post without a new image call.
 */

export interface AdFontFace {
  path: string;
  weight: string;
  format: "woff2" | "truetype";
}

export interface AdFont {
  id: string;
  family: string;
  faces: AdFontFace[];
}

export const DEFAULT_FONT_ID = "vazirmatn";

export const AD_FONTS: readonly AdFont[] = [
  {
    id: "vazirmatn",
    family: "Vazirmatn",
    faces: [
      {
        path: "/fonts/vazirmatn-arabic-wght-normal.woff2",
        weight: "100 900",
        format: "woff2",
      },
      {
        path: "/fonts/vazirmatn-latin-wght-normal.woff2",
        weight: "100 900",
        format: "woff2",
      },
    ],
  },
  {
    id: "estedad",
    family: "Estedad",
    faces: [
      { path: "/fonts/estedad-arabic-400.woff2", weight: "400", format: "woff2" },
      { path: "/fonts/estedad-arabic-700.woff2", weight: "700", format: "woff2" },
      { path: "/fonts/estedad-latin-400.woff2", weight: "400", format: "woff2" },
      { path: "/fonts/estedad-latin-700.woff2", weight: "700", format: "woff2" },
    ],
  },
  {
    id: "gandom",
    family: "Gandom",
    faces: [{ path: "/fonts/gandom-regular.ttf", weight: "400", format: "truetype" }],
  },
  {
    id: "amiri",
    family: "Amiri",
    faces: [
      { path: "/fonts/amiri-arabic-400.woff2", weight: "400", format: "woff2" },
      { path: "/fonts/amiri-arabic-700.woff2", weight: "700", format: "woff2" },
    ],
  },
  {
    id: "lalezar",
    family: "Lalezar",
    faces: [
      { path: "/fonts/lalezar-arabic-400.woff2", weight: "400", format: "woff2" },
      { path: "/fonts/lalezar-latin-400.woff2", weight: "400", format: "woff2" },
    ],
  },
];

export const AD_FONT_IDS = AD_FONTS.map((font) => font.id);

export function getAdFont(id: string | null | undefined): AdFont {
  return AD_FONTS.find((font) => font.id === id) ?? AD_FONTS[0];
}

export function fontFamilyCss(id: string | null | undefined): string {
  return `"${getAdFont(id).family}", "Vazirmatn", ui-sans-serif, sans-serif`;
}
