"use client";

import { useEffect, useState } from "react";
import { chatApi } from "@/lib/api/chat";
import type { ConversationSummary } from "@/lib/api/chat/types";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { ChatSheet } from "./primitives/ChatSheet";

export function ChatArchiveSheet({
  open,
  revision,
  onClose,
  onRestore,
  onDelete,
}: {
  open: boolean;
  revision: number;
  onClose: () => void;
  onRestore: (id: string) => Promise<void>;
  onDelete: (id: string) => void;
}) {
  const { t } = useI18n();
  const [items, setItems] = useState<ConversationSummary[]>([]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void chatApi.listArchivedConversations().then((next) => {
      if (!cancelled) setItems(next);
    });
    return () => {
      cancelled = true;
    };
  }, [open, revision]);

  async function restore(id: string) {
    await onRestore(id);
    setItems((current) => current.filter((item) => item.id !== id));
  }

  return (
    <ChatSheet
      open={open}
      onClose={onClose}
      title={t("chat.archivedChats")}
      dataChat="archive-sheet"
      overlayClassName="z-[60]"
    >
      {items.length === 0 ? (
        <p className="pb-6 text-sm text-chat-text-secondary">
          {t("chat.archiveEmpty")}
        </p>
      ) : (
        <ul className="flex flex-col gap-2 pb-4">
          {items.map((item) => (
            <li
              key={item.id}
              data-chat-archived={item.id}
              className="flex items-center gap-2 rounded-chat-md bg-chat-surface-secondary px-3 py-2"
            >
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-chat-text">
                {item.title}
              </span>
              <button
                type="button"
                data-chat="archive-restore"
                onClick={() => void restore(item.id)}
                className="h-11 shrink-0 rounded-full px-3 text-sm font-semibold text-chat-accent"
              >
                {t("chat.restore")}
              </button>
              <button
                type="button"
                data-chat="archive-delete"
                onClick={() => onDelete(item.id)}
                className="h-11 shrink-0 rounded-full px-3 text-sm font-semibold text-chat-danger"
              >
                {t("chat.delete")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </ChatSheet>
  );
}
