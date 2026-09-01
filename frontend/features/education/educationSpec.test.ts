import { describe, expect, it } from "vitest";
import {
  AD_COMPOSITION_KEYS,
  buildEducationalRenderSpec,
  canSaveGeneratedTheme,
  isEducationalRenderSpec,
  EDUCATION_RENDER_MODE,
} from "./educationSpec";

describe("educationSpec", () => {
  it("stores only render_mode and the image path", () => {
    const spec = buildEducationalRenderSpec("supabase://education/p1/post.jpg");
    expect(spec.render_mode).toBe(EDUCATION_RENDER_MODE);
    expect(spec.image_path).toBe("supabase://education/p1/post.jpg");
    expect(isEducationalRenderSpec(spec)).toBe(true);
    for (const key of AD_COMPOSITION_KEYS) {
      expect(spec).not.toHaveProperty(key);
    }
  });

  it("rejects ad composition fields", () => {
    expect(
      isEducationalRenderSpec({
        render_mode: "educational",
        image_path: "x",
        cta_fa: "شروع",
      }),
    ).toBe(false);
    expect(
      isEducationalRenderSpec({
        render_mode: "educational",
        text_layers: [{ text: "امتیاز 100" }],
      }),
    ).toBe(false);
    expect(
      isEducationalRenderSpec({
        render_mode: "advertising",
        image_path: "x",
      }),
    ).toBe(false);
  });

  it("offers save-theme only when Afarin designed the look", () => {
    expect(
      canSaveGeneratedTheme({
        selected_theme_id: null,
        selected_builtin_theme_id: null,
      }),
    ).toBe(true);
    expect(
      canSaveGeneratedTheme({
        selected_theme_id: "t1",
        selected_builtin_theme_id: null,
      }),
    ).toBe(false);
    expect(
      canSaveGeneratedTheme({
        selected_theme_id: null,
        selected_builtin_theme_id: "chalkboard",
      }),
    ).toBe(false);
  });
});
