import { describe, expect, it } from "vitest";
import { AD_FONTS, AD_FONT_IDS } from "./fonts";

describe("ad font catalog", () => {
  it("ships a small OFL Persian set including Vazirmatn", () => {
    expect(AD_FONT_IDS).toEqual([
      "vazirmatn",
      "estedad",
      "gandom",
      "amiri",
      "lalezar",
    ]);
    expect(AD_FONTS.every((font) => font.faces.length > 0)).toBe(true);
  });
});
