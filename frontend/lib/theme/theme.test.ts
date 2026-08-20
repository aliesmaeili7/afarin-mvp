import { afterEach, describe, expect, it } from "vitest";
import { THEME_COOKIE } from "./cookies";
import { parseThemePreference, resolveDarkClass } from "./resolve";
import { DEFAULT_THEME } from "./types";
import { readBrowserCookie, writeBrowserCookie } from "@/lib/i18n/cookies";

describe("theme preference", () => {
  it("defaults to system", () => {
    expect(parseThemePreference(undefined)).toBe(DEFAULT_THEME);
    expect(parseThemePreference("nope")).toBe("system");
    expect(parseThemePreference("dark")).toBe("dark");
    expect(parseThemePreference("light")).toBe("light");
  });

  it("resolves light, dark, and system against the media query", () => {
    expect(resolveDarkClass("light", true)).toBe(false);
    expect(resolveDarkClass("dark", false)).toBe(true);
    expect(resolveDarkClass("system", true)).toBe(true);
    expect(resolveDarkClass("system", false)).toBe(false);
  });

  it("round-trips the theme cookie", () => {
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

    writeBrowserCookie(THEME_COOKIE, "light");
    expect(parseThemePreference(readBrowserCookie(THEME_COOKIE))).toBe("light");
  });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, "document");
});
