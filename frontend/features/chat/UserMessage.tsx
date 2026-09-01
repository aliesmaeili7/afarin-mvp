"use client";

import { messageDirFromLanguage } from "./chatDirection";
import type { ConversationMessage } from "@/lib/api/chat/types";

export function UserMessage({ message }: { message: ConversationMessage }) {
  const dir = messageDirFromLanguage(message.language);
  const attachment = message.metadata_json?.attachment;

  return (
    <div className="flex justify-end" data-chat="user-message">
      <div
        dir={dir}
        className="max-w-[78%] rounded-chat-lg bg-chat-surface-secondary px-4 py-2.5 text-[0.95rem] leading-8 text-chat-text shadow-chat-soft"
      >
        {message.content ? <p className="whitespace-pre-wrap">{message.content}</p> : null}
        {attachment ? (
          <p className="mt-1 text-xs text-chat-text-secondary">{attachment.name}</p>
        ) : null}
      </div>
    </div>
  );
}
