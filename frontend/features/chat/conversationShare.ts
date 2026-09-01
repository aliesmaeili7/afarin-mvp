import type { Conversation } from "@/lib/api/chat/types";

export function formatConversationShareText(conversation: Conversation): string {
  const speaker = (role: Conversation["messages"][number]["role"]) => {
    if (role === "user") {
      return conversation.language === "en" ? "You" : "شما";
    }
    return conversation.language === "en" ? "Afarin" : "آفرین";
  };

  const lines = [conversation.title.trim(), ""];
  for (const message of conversation.messages) {
    const content = message.content.trim();
    if (!content) continue;
    lines.push(`${speaker(message.role)}: ${content}`);
  }
  return lines.join("\n").trim();
}

export function canShareNatively(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.share === "function";
}

export type ShareSheetOption = "copyText" | "native" | "copyLink";

export function shareSheetOptions(
  publicUrl: string | null,
  nativeShare: boolean,
): ShareSheetOption[] {
  const options: ShareSheetOption[] = ["copyText"];
  if (nativeShare) options.push("native");
  if (publicUrl) options.push("copyLink");
  return options;
}
