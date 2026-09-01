export interface ComposerKeyEvent {
  key: string;
  shiftKey: boolean;
  isComposing?: boolean;
}

/**
 * Desktop (fine pointer): Enter sends, Shift+Enter inserts a newline.
 * Coarse pointer / mobile: Enter always inserts a newline; send is the button.
 */
export function shouldSendOnEnter(
  event: ComposerKeyEvent,
  coarsePointer: boolean,
): boolean {
  if (event.key !== "Enter") return false;
  if (event.shiftKey) return false;
  if (event.isComposing) return false;
  return !coarsePointer;
}

export function detectCoarsePointer(
  media: Pick<MediaQueryList, "matches"> | null,
): boolean {
  return media?.matches ?? false;
}
