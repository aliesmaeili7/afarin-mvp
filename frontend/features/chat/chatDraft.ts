const DRAFT_KEY = "afarin:chat-draft";

export interface ChatDraft {
  content: string;
  themeId: string | null;
  creationAction: "advertising" | "education" | "general_image" | null;
}

function storage(): Storage | null {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

export function readChatDraft(): ChatDraft | null {
  const store = storage();
  if (!store) return null;
  try {
    const raw = store.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatDraft;
    if (typeof parsed?.content !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeChatDraft(draft: ChatDraft): void {
  storage()?.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export function clearChatDraft(): void {
  storage()?.removeItem(DRAFT_KEY);
}
