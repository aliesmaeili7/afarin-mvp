import type { EducationalRenderSpec } from "@/types/domain";

export const EDUCATION_RENDER_MODE = "educational" as const;

/** Advertising compositor fields. Educational specs must never grow these. */
export const AD_COMPOSITION_KEYS = [
  "template_id",
  "background_id",
  "headline_fa",
  "subheadline_fa",
  "cta_fa",
  "price_text",
  "brand_name",
  "product_image_path",
  "product_source",
  "slide_label_fa",
  "text_layers",
  "scene_image_path",
] as const;

export function buildEducationalRenderSpec(
  imagePath: string | null,
): EducationalRenderSpec {
  return {
    render_mode: EDUCATION_RENDER_MODE,
    image_path: imagePath,
  };
}

export function isEducationalRenderSpec(
  spec: Record<string, unknown> | EducationalRenderSpec,
): spec is EducationalRenderSpec {
  if (spec.render_mode !== EDUCATION_RENDER_MODE) return false;
  return AD_COMPOSITION_KEYS.every((key) => !(key in spec));
}

/** Save-this-theme is only offered when Afarin designed the look. */
export function canSaveGeneratedTheme(post: {
  selected_theme_id: string | null;
  selected_builtin_theme_id: string | null;
}): boolean {
  return !post.selected_theme_id && !post.selected_builtin_theme_id;
}
