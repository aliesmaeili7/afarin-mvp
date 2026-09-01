import { describe, expect, it } from "vitest";
import {
  AD_CREATE_HREF,
  EDUCATION_CREATE_HREF,
} from "./PathChooser";
import { t } from "@/lib/i18n/t";

describe("homepage content paths", () => {
  it("offers advertising and educational entry points", () => {
    expect(AD_CREATE_HREF).toBe("/create");
    expect(EDUCATION_CREATE_HREF).toBe("/create/education");
  });

  it("no longer frames the product as advertising-only", () => {
    const faHero = `${t("fa", "landing.heroBefore")} ${t("fa", "landing.heroHighlight")}`;
    const faSub = t("fa", "landing.subtitle");
    expect(faHero).toContain("پست آماده اینستاگرام");
    expect(faSub).toMatch(/تبلیغ/);
    expect(faSub).toMatch(/درس|آموزش/);
    expect(t("fa", "landing.pathAd")).toBe("تبلیغاتی");
    expect(t("fa", "landing.pathEdu")).toBe("آموزشی");
    expect(t("en", "landing.pathAdCta")).toMatch(/ad/i);
    expect(t("en", "landing.pathEduCta")).toMatch(/teaching/i);
  });
});
