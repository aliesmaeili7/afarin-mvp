"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  applyLocaleToDocument,
  LOCALE_COOKIE,
  localeDir,
  writeBrowserCookie,
} from "./cookies";
import { t, type Translate, type TranslationKey } from "./t";
import { toDisplayError } from "./errors";
import type { Locale } from "./types";
import { THEME_COOKIE } from "@/lib/theme/cookies";
import { applyThemeToDocument } from "@/lib/theme/resolve";
import type { ThemePreference } from "@/lib/theme/types";

interface PreferencesValue {
  locale: Locale;
  theme: ThemePreference;
  dir: "rtl" | "ltr";
  settingsOpen: boolean;
  setLocale: (locale: Locale) => void;
  setTheme: (theme: ThemePreference) => void;
  openSettings: () => void;
  closeSettings: () => void;
  t: Translate;
}

const PreferencesContext = createContext<PreferencesValue | null>(null);

export function PreferencesProvider({
  locale: initialLocale,
  theme: initialTheme,
  children,
}: {
  locale: Locale;
  theme: ThemePreference;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState(initialLocale);
  const [theme, setThemeState] = useState(initialTheme);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyThemeToDocument("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

  const setLocale = useCallback((next: Locale) => {
    writeBrowserCookie(LOCALE_COOKIE, next);
    applyLocaleToDocument(next);
    setLocaleState(next);
  }, []);

  const setTheme = useCallback((next: ThemePreference) => {
    writeBrowserCookie(THEME_COOKIE, next);
    applyThemeToDocument(next);
    setThemeState(next);
  }, []);

  const openSettings = useCallback(() => setSettingsOpen(true), []);
  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  const value = useMemo<PreferencesValue>(
    () => ({
      locale,
      theme,
      dir: localeDir(locale),
      settingsOpen,
      setLocale,
      setTheme,
      openSettings,
      closeSettings,
      t: (key: TranslationKey, vars) => t(locale, key, vars),
    }),
    [
      locale,
      theme,
      settingsOpen,
      setLocale,
      setTheme,
      openSettings,
      closeSettings,
    ],
  );

  return (
    <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
  );
}

export function useI18n(): PreferencesValue {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error("useI18n must be used inside <PreferencesProvider>");
  }
  return context;
}

export function useDisplayError() {
  const { locale } = useI18n();
  return useCallback((error: unknown) => toDisplayError(error, locale), [locale]);
}
