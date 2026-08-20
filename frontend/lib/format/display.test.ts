import { afterEach, describe, expect, it, vi } from "vitest";
import { formatDigits, formatPercent, formatRelativeDay } from "./display";

describe("locale-aware chrome formatting", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("uses Persian digits in fa and Latin digits in en", () => {
    expect(formatDigits(12, "fa")).toBe("۱۲");
    expect(formatDigits(12, "en")).toBe("12");
    expect(formatPercent(40, "fa")).toBe("٪۴۰");
    expect(formatPercent(40, "en")).toBe("40%");
  });

  it("uses English relative dates in en", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-20T12:00:00Z"));
    expect(formatRelativeDay("2026-08-20T08:00:00Z", "en")).toBe("Today");
    expect(formatRelativeDay("2026-08-19T08:00:00Z", "en")).toBe("Yesterday");
    expect(formatRelativeDay("2026-08-17T08:00:00Z", "en")).toBe("3 days ago");
  });
});
