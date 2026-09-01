const ARABIC_SCRIPT =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/u;

export type MessageDir = "rtl" | "ltr";
export type MessageLanguage = "fa" | "en";

/**
 * Infer conversation direction from the latest user text.
 *
 * Persian is the default. Mixed messages stay RTL when Persian/Arabic
 * letters are the conversational structure, even with English product terms.
 */
export function inferMessageDir(text: string): MessageDir {
  const letters = [...text].filter((char) => /\p{L}/u.test(char));
  if (letters.length === 0) return "rtl";

  const arabicCount = letters.filter((char) => ARABIC_SCRIPT.test(char)).length;
  const ratio = arabicCount / letters.length;
  return ratio >= 0.15 ? "rtl" : "ltr";
}

export function inferMessageLanguage(text: string): MessageLanguage {
  return inferMessageDir(text) === "rtl" ? "fa" : "en";
}

export function messageDirFromLanguage(
  language: MessageLanguage | null | undefined,
): MessageDir {
  return language === "en" ? "ltr" : "rtl";
}
