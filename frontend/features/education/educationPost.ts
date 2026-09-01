import type { EducationalPost, EducationalRenderSpec } from "@/types/domain";

export { canSaveGeneratedTheme } from "./educationSpec";

/** 1080×1080. The only educational format in Phase 1. */
export const EDUCATION_POST_SIZE = { width: 1080, height: 1080 } as const;

export function listingTitle(prompt: string, limit = 80): string {
  return prompt.trim().replace(/\s+/g, " ").slice(0, limit);
}

/**
 * The prompt's language decides download/filename direction, so an English
 * lesson reads left-to-right even though the surrounding app is Persian-first.
 */
export function postDirection(post: EducationalPost): "rtl" | "ltr" {
  return post.language === "en" ? "ltr" : "rtl";
}

function isFilled(value: object): boolean {
  return Object.keys(value).length > 0;
}

export function postTheme(post: EducationalPost) {
  return isFilled(post.theme_json) ? post.theme_json : null;
}

export function postRenderSpec(post: EducationalPost): EducationalRenderSpec | null {
  if (!isFilled(post.render_spec_json)) return null;
  return post.render_spec_json as EducationalRenderSpec;
}

/** The theme name to show next to "save this theme". */
export function themeLabel(post: EducationalPost): string | null {
  return postTheme(post)?.name ?? null;
}
