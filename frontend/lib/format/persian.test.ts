import { describe, expect, it } from "vitest";
import {
  formatToman,
  normalizePersian,
  toLatinDigits,
  toPersianDigits,
} from "./persian";

describe("toPersianDigits", () => {
  it("converts Latin digits and leaves other characters alone", () => {
    expect(toPersianDigits("۳ / 5")).toBe("۳ / ۵");
    expect(toPersianDigits(1404)).toBe("۱۴۰۴");
    expect(toPersianDigits("قیمت 399 تومان")).toBe("قیمت ۳۹۹ تومان");
  });
});

describe("toLatinDigits", () => {
  it("converts both Persian and Arabic-Indic digits", () => {
    expect(toLatinDigits("۱۲۳")).toBe("123");
    expect(toLatinDigits("٤٥٦")).toBe("456");
  });
});

describe("normalizePersian", () => {
  it("normalises Arabic ي and ك to their Persian forms", () => {
    expect(normalizePersian("يك كتاب")).toBe("یک کتاب");
  });

  it("preserves the ZWNJ used for نیم‌فاصله", () => {
    const value = "نیم\u200Cفاصله";
    expect(normalizePersian(value)).toContain("\u200C");
  });

  it("strips tatweel and stray bidi marks", () => {
    expect(normalizePersian("سلامـــ\u200E")).toBe("سلام");
  });
});

describe("formatToman", () => {
  it("groups thousands and appends the currency", () => {
    expect(formatToman(399000)).toContain("تومان");
  });
});
