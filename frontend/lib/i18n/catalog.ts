import type { Locale } from "./types";
import { t, type TranslationKey } from "./t";

const STYLE_IDS = [
  "photoreal_commercial",
  "fashion_editorial",
  "anime",
  "manga_illustrated",
  "render_3d",
  "clay",
  "collage",
  "surreal",
  "cinematic",
  "retro",
  "watercolor_illustration",
  "neon",
  "persian_miniature_inspired",
  "vintage_iranian_poster",
] as const;

const TEMPLATE_IDS = [
  "hero_product",
  "model_using",
  "product_pedestal",
  "magazine_cover",
  "giant_miniature_world",
  "cinematic_environment",
  "floating_product",
  "flat_lay",
  "character_poster",
  "illustrated_scene",
  "product_with_props",
  "surreal_scale",
] as const;

export const VISUAL_STYLE_IDS = STYLE_IDS;
export const VISUAL_TEMPLATE_IDS = TEMPLATE_IDS;
export const VISUAL_CATALOG_IDS = [...STYLE_IDS, ...TEMPLATE_IDS] as const;

export type VisualStyleId = (typeof STYLE_IDS)[number];
export type VisualTemplateId = (typeof TEMPLATE_IDS)[number];

function isStyleId(id: string): id is VisualStyleId {
  return (STYLE_IDS as readonly string[]).includes(id);
}

function isTemplateId(id: string): id is VisualTemplateId {
  return (TEMPLATE_IDS as readonly string[]).includes(id);
}

export function catalogLabel(
  locale: Locale,
  kind: "styles" | "templates",
  id: string,
  fallback: string,
): string {
  if (isStyleId(id)) {
    return t(locale, `visual.styles.${id}.label` as TranslationKey);
  }
  if (isTemplateId(id)) {
    return t(locale, `visual.templates.${id}.label` as TranslationKey);
  }
  void kind;
  return fallback;
}

export function catalogDescription(
  locale: Locale,
  kind: "styles" | "templates",
  id: string,
  fallback: string,
): string {
  if (isStyleId(id)) {
    return t(locale, `visual.styles.${id}.description` as TranslationKey);
  }
  if (isTemplateId(id)) {
    return t(locale, `visual.templates.${id}.description` as TranslationKey);
  }
  void kind;
  return fallback;
}
