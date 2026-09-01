import type { ChatTheme, ChatThemeSnapshot } from "./types";

export const CHAT_THEMES: ChatTheme[] = [
  {
    id: "saved-clay",
    name: "خمیری و بازیگوش",
    group: "saved",
    swatch: "linear-gradient(135deg, #f6c27a, #f08a5d)",
  },
  {
    id: "saved-math",
    name: "ریاضی بنفش",
    group: "saved",
    swatch: "linear-gradient(135deg, #7c3aed, #c3a7ff)",
  },
  {
    id: "catalog-clay",
    name: "Clay",
    group: "catalog",
    swatch: "linear-gradient(135deg, #e7c9a5, #d4a574)",
  },
  {
    id: "catalog-pastel",
    name: "Pastel",
    group: "catalog",
    swatch: "linear-gradient(135deg, #f8d5e0, #cde7f0)",
  },
  {
    id: "catalog-modern",
    name: "Modern",
    group: "catalog",
    swatch: "linear-gradient(135deg, #17121f, #6c6382)",
  },
];

export function themeSnapshot(theme: ChatTheme): ChatThemeSnapshot {
  return {
    id: theme.id,
    source: "chat_catalog",
    name: theme.name,
    style_json: {},
  };
}

export function snapshotForThemeId(themeId: string | null): ChatThemeSnapshot | null {
  if (!themeId) return null;
  const theme = CHAT_THEMES.find((item) => item.id === themeId);
  return theme ? themeSnapshot(theme) : null;
}

export function catalogTheme(
  snapshot: ChatThemeSnapshot | null,
  themes: ChatTheme[],
): ChatTheme | null {
  if (!snapshot) return null;
  return (
    themes.find((item) => item.id === snapshot.id) ?? {
      id: snapshot.id,
      name: snapshot.name,
      group: "catalog",
      swatch: "linear-gradient(135deg, #c4b5d4, #8b7aa0)",
    }
  );
}
