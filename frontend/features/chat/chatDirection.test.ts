import { describe, expect, it } from "vitest";
import { inferMessageDir, inferMessageLanguage } from "./chatDirection";

describe("inferMessageDir", () => {
  it("treats Persian as RTL", () => {
    expect(inferMessageDir("برای کلاس ششم یه پست بامزه بساز")).toBe("rtl");
    expect(inferMessageLanguage("برای کلاس ششم یه پست بامزه بساز")).toBe("fa");
  });

  it("treats English as LTR", () => {
    expect(inferMessageDir("Make an elegant Instagram ad for this shoe.")).toBe(
      "ltr",
    );
    expect(
      inferMessageLanguage("Make an elegant Instagram ad for this shoe."),
    ).toBe("en");
  });

  it("keeps mixed Persian conversation structure as RTL", () => {
    expect(
      inferMessageDir("برای این محصول یه luxury ad با vibe مینیمال بساز"),
    ).toBe("rtl");
  });

  it("defaults empty text to RTL", () => {
    expect(inferMessageDir("")).toBe("rtl");
    expect(inferMessageDir("   ")).toBe("rtl");
  });
});
