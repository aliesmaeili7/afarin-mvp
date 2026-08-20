import { en } from "./dictionaries/en";
import { fa } from "./dictionaries/fa";
import type { DeepStringify, Locale } from "./types";

export const dictionaries = { fa, en };

export type Dictionary = DeepStringify<typeof fa>;

type Paths<T> = {
  [K in keyof T & string]: T[K] extends string
    ? K
    : `${K}.${Paths<T[K]>}`
}[keyof T & string];

export type TranslationKey = Paths<Dictionary>;

export type Translate = (
  key: TranslationKey,
  vars?: Record<string, string | number>,
) => string;

function lookup(dict: Dictionary, key: string): string {
  const parts = key.split(".");
  let node: unknown = dict;
  for (const part of parts) {
    if (typeof node !== "object" || node === null) return key;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : key;
}

export function t(
  locale: Locale,
  key: TranslationKey,
  vars?: Record<string, string | number>,
): string {
  let value = lookup(dictionaries[locale], key);
  if (!vars) return value;
  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export function dictionaryKeys(dict: object, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [name, value] of Object.entries(dict)) {
    const path = prefix ? `${prefix}.${name}` : name;
    if (typeof value === "string") keys.push(path);
    else if (value && typeof value === "object") {
      keys.push(...dictionaryKeys(value, path));
    }
  }
  return keys;
}
