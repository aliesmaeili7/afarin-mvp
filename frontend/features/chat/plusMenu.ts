import type { TranslationKey } from "@/lib/i18n/t";

export type CreationAction = "advertising" | "education" | "general_image";

export type PlusMenuId =
  | CreationAction
  | "upload"
  | "theme";

export type PlusMenuKind = "creation" | "upload" | "theme";

export interface PlusMenuItem {
  id: PlusMenuId;
  kind: PlusMenuKind;
  /** Value for `data-chat-action`. */
  action: string;
  labelKey: TranslationKey;
  chipKey?: TranslationKey;
}

export const PLUS_MENU_ITEMS: readonly PlusMenuItem[] = [
  {
    id: "advertising",
    kind: "creation",
    action: "advertising",
    labelKey: "chat.plusAd",
    chipKey: "chat.actionAd",
  },
  {
    id: "education",
    kind: "creation",
    action: "education",
    labelKey: "chat.plusEdu",
    chipKey: "chat.actionEdu",
  },
  {
    id: "general_image",
    kind: "creation",
    action: "generate",
    labelKey: "chat.generateImage",
    chipKey: "chat.actionImage",
  },
  {
    id: "upload",
    kind: "upload",
    action: "upload",
    labelKey: "chat.upload",
  },
  {
    id: "theme",
    kind: "theme",
    action: "theme",
    labelKey: "chat.chooseTheme",
  },
];

export const CREATION_ACTION_CHIPS: Record<CreationAction, TranslationKey> = {
  advertising: "chat.actionAd",
  education: "chat.actionEdu",
  general_image: "chat.actionImage",
};

export interface ComposerContext {
  creationAction: CreationAction | null;
  themeId: string | null;
  attachmentName: string | null;
}

export function emptyComposerContext(): ComposerContext {
  return { creationAction: null, themeId: null, attachmentName: null };
}

/** Selecting a creation action replaces any previous primary action. */
export function selectCreationAction(
  context: ComposerContext,
  action: CreationAction,
): ComposerContext {
  return { ...context, creationAction: action };
}

/** Removing the chip returns to automatic skill routing. */
export function clearCreationAction(context: ComposerContext): ComposerContext {
  return { ...context, creationAction: null };
}

export function setComposerTheme(
  context: ComposerContext,
  themeId: string | null,
): ComposerContext {
  return { ...context, themeId };
}

export function setComposerAttachment(
  context: ComposerContext,
  attachmentName: string | null,
): ComposerContext {
  return { ...context, attachmentName };
}

export function plusMenuHrefs(
  items: readonly PlusMenuItem[] = PLUS_MENU_ITEMS,
): string[] {
  return items.flatMap((item) => {
    if ("href" in item && typeof (item as { href?: unknown }).href === "string") {
      return [(item as { href: string }).href];
    }
    return [];
  });
}

export function isCreationAction(id: PlusMenuId): id is CreationAction {
  return id === "advertising" || id === "education" || id === "general_image";
}

export function skillHintFromAction(
  action: CreationAction | null,
): CreationAction | null {
  return action;
}
