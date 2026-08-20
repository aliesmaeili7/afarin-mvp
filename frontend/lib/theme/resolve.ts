import { DEFAULT_THEME, isThemePreference, type ThemePreference } from "./types";

export function parseThemePreference(
  value: string | null | undefined,
): ThemePreference {
  return isThemePreference(value) ? value : DEFAULT_THEME;
}

export function resolveDarkClass(
  preference: ThemePreference,
  systemDark: boolean,
): boolean {
  if (preference === "dark") return true;
  if (preference === "light") return false;
  return systemDark;
}

export function applyThemeToDocument(preference: ThemePreference): void {
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = resolveDarkClass(preference, systemDark);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.setAttribute("data-theme", preference);
}
