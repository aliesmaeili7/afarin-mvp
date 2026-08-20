import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { dictionaries, dictionaryKeys, t } from "./t";
import {
  LOCALE_COOKIE,
  localeDir,
  parseLocale,
  readBrowserCookie,
  writeBrowserCookie,
} from "./cookies";
import { DEFAULT_LOCALE } from "./types";
import {
  catalogDescription,
  catalogLabel,
  VISUAL_STYLE_IDS,
  VISUAL_TEMPLATE_IDS,
} from "./catalog";
import { generationStageMessage, toDisplayError } from "./errors";
import { ApiError } from "@/lib/api/types";
import { AD_FONT_IDS } from "@/features/campaign/ad-renderer/fonts";
import {
  AUDIENCE_SUGGESTIONS,
  SUGGESTED_AUDIENCE,
} from "@/lib/content/objectives";
import { HERO_EXAMPLE } from "@/lib/content/landingExamples";
import { THEME_COOKIE } from "@/lib/theme/cookies";
import { parseThemePreference } from "@/lib/theme/resolve";

describe("locale defaults", () => {
  it("treats a missing cookie as Persian", () => {
    expect(parseLocale(undefined)).toBe(DEFAULT_LOCALE);
    expect(parseLocale(null)).toBe("fa");
    expect(parseLocale("de")).toBe("fa");
    expect(parseLocale("en")).toBe("en");
  });

  it("maps locale to document direction", () => {
    expect(localeDir("fa")).toBe("rtl");
    expect(localeDir("en")).toBe("ltr");
  });
});

describe("dictionaries", () => {
  it("has the same keys in fa and en", () => {
    expect(dictionaryKeys(dictionaries.en).sort()).toEqual(
      dictionaryKeys(dictionaries.fa).sort(),
    );
  });

  it("returns Persian by default and English when asked", () => {
    expect(t("fa", "common.save")).toBe("ذخیره");
    expect(t("en", "common.save")).toBe("Save");
    expect(t("en", "wizard.letAfarin")).toBe("Let Afarin suggest");
    expect(t("en", "result.generateThree")).toBe("Generate 3 new versions");
  });

  it("interpolates variables", () => {
    expect(t("en", "wizard.conceptBadge", { n: 2 })).toBe("Idea 2");
    expect(t("fa", "wizard.conceptBadge", { n: 2 })).toBe("ایده 2");
  });
});

describe("visual catalog labels", () => {
  it("covers every backend style and template id", () => {
    const catalogPath = join(
      dirname(fileURLToPath(import.meta.url)),
      "../../../backend/app/content/visual_catalog.json",
    );
    const catalog = JSON.parse(readFileSync(catalogPath, "utf8")) as {
      styles: { id: string }[];
      templates: { id: string }[];
    };
    expect(VISUAL_STYLE_IDS).toEqual(catalog.styles.map((item) => item.id));
    expect(VISUAL_TEMPLATE_IDS).toEqual(catalog.templates.map((item) => item.id));
  });

  it("translates every style and template id", () => {
    for (const id of VISUAL_STYLE_IDS) {
      expect(catalogLabel("en", "styles", id, "x")).not.toBe("x");
      expect(catalogLabel("fa", "styles", id, "x")).not.toBe("x");
      expect(catalogDescription("en", "styles", id, "x")).not.toBe("x");
    }
    for (const id of VISUAL_TEMPLATE_IDS) {
      expect(catalogLabel("en", "templates", id, "x")).not.toBe("x");
      expect(catalogLabel("fa", "templates", id, "x")).not.toBe("x");
    }
  });

  it("translates every ad font id", () => {
    for (const id of AD_FONT_IDS) {
      expect(t("en", `ad.font.${id}.label` as Parameters<typeof t>[1])).not.toBe(
        `ad.font.${id}.label`,
      );
      expect(t("fa", `ad.font.${id}.label` as Parameters<typeof t>[1])).not.toBe(
        `ad.font.${id}.label`,
      );
    }
  });

  it("does not rewrite campaign copy fixtures", () => {
    expect(catalogLabel("en", "styles", "not_a_style", "fallback")).toBe("fallback");
    expect(HERO_EXAMPLE.spec.headline_fa).toBe("هدیه‌ای با عطر ایران");
    expect(t("en", "common.save")).not.toBe(HERO_EXAMPLE.spec.headline_fa);
  });
});

describe("audience persistence", () => {
  it("keeps chip and suggested values in Persian", () => {
    const persian = /[\u0600-\u06FF]/;
    for (const chip of AUDIENCE_SUGGESTIONS) {
      expect(chip.value_fa).toMatch(persian);
      expect(t("en", `campaign.audience.${chip.id}` as Parameters<typeof t>[1])).not.toBe(
        chip.value_fa,
      );
    }
    for (const value of Object.values(SUGGESTED_AUDIENCE)) {
      expect(value).toMatch(persian);
    }
  });
});

describe("cookie round-trip", () => {
  it("writes locale and theme cookies the browser can parse", () => {
    const store = new Map<string, string>();
    Object.defineProperty(globalThis, "document", {
      configurable: true,
      value: {
        get cookie() {
          return [...store.entries()]
            .map(([name, value]) => `${name}=${value}`)
            .join("; ");
        },
        set cookie(value: string) {
          const pair = value.split(";")[0] ?? "";
          const eq = pair.indexOf("=");
          store.set(pair.slice(0, eq), pair.slice(eq + 1));
        },
      },
    });

    writeBrowserCookie(LOCALE_COOKIE, "en");
    writeBrowserCookie(THEME_COOKIE, "dark");
    expect(parseLocale(readBrowserCookie(LOCALE_COOKIE))).toBe("en");
    expect(parseThemePreference(readBrowserCookie(THEME_COOKIE))).toBe("dark");
  });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, "document");
});

describe("API error display", () => {
  it("maps known Persian payloads to English", () => {
    const error = new ApiError("not_found", "این کمپین پیدا نشد.");
    expect(toDisplayError(error, "en")).toBe("This campaign wasn’t found.");
    expect(toDisplayError(error, "fa")).toBe("این کمپین پیدا نشد.");
  });

  it("localizes generation stages by id, not by generated campaign text", () => {
    expect(generationStageMessage("en", "captions", "در حال نوشتن کپشن‌ها…")).toBe(
      "Writing captions…",
    );
    expect(generationStageMessage("fa", "visual", null)).toBe(
      "در حال ساخت تصویر محصول…",
    );
  });
});
