import { describe, expect, it } from "vitest";
import { activityCopy, preparingPhaseFor } from "./chatActivity";

describe("chat activity copy", () => {
  it("maps phases to Persian", () => {
    expect(activityCopy("thinking", "fa")).toBe("دارم بررسی می‌کنم…");
    expect(activityCopy("preparing_education", "fa")).toBe(
      "دارم پست آموزشی رو آماده می‌کنم…",
    );
    expect(activityCopy("preparing_advertising", "fa")).toBe(
      "دارم تبلیغت رو آماده می‌کنم…",
    );
    expect(activityCopy("preparing_image", "fa")).toBe(
      "دارم تصویر رو آماده می‌کنم…",
    );
    expect(activityCopy("generating_image", "fa")).toBe(
      "دارم تصویرت رو می‌سازم…",
    );
    expect(activityCopy("finalizing", "fa")).toBe("دارم نتیجه رو آماده می‌کنم…");
  });

  it("maps phases to English", () => {
    expect(activityCopy("thinking", "en")).toBe("Thinking…");
    expect(activityCopy("preparing_education", "en")).toBe(
      "Preparing your educational post…",
    );
    expect(activityCopy("generating_image", "en")).toBe("Creating your image…");
    expect(activityCopy("finalizing", "en")).toBe("Finishing up…");
  });

  it("does not use artifact language", () => {
    expect(activityCopy("generating_image", "fa")).toContain("تصویرت");
    expect(activityCopy("generating_image", "en")).toContain("Creating");
  });

  it("uses plural ads copy when three images are requested", () => {
    expect(activityCopy("generating_image", "fa", { imageCount: 3 })).toBe(
      "دارم تصاویر تبلیغت رو می‌سازم…",
    );
    expect(activityCopy("generating_image", "en", { imageCount: 3 })).toBe(
      "Creating your ads…",
    );
  });

  it("defaults unknown phase to thinking in Persian", () => {
    expect(activityCopy("calling_gpt", "fa")).toBe("دارم بررسی می‌کنم…");
    expect(activityCopy(null, null)).toBe("دارم بررسی می‌کنم…");
  });

  it("maps explicit routes to preparing phases, not thinking", () => {
    expect(preparingPhaseFor("education")).toBe("preparing_education");
    expect(preparingPhaseFor("advertising")).toBe("preparing_advertising");
    expect(preparingPhaseFor("general_image")).toBe("preparing_image");
    expect(preparingPhaseFor(null)).toBe("thinking");
  });

  it("does not expose internal names", () => {
    const blob = [
      activityCopy("preparing_education", "fa"),
      activityCopy("generating_image", "en"),
      activityCopy("finalizing", "fa"),
    ].join(" ");
    expect(blob).not.toMatch(/GPT|OpenRouter|Seedream|EducationalAgent|skill/i);
  });
});
