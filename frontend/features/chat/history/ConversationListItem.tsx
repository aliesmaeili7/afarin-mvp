"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ConversationSummary } from "@/lib/api/chat/types";
import type { ConversationControls } from "./conversationControls";
import { ConversationOverflowMenu } from "./ConversationOverflowMenu";

export function ConversationListItem({
  item,
  active,
  onNavigate,
  controls,
}: {
  item: ConversationSummary;
  active: boolean;
  onNavigate?: () => void;
  controls: ConversationControls;
}) {
  const { t } = useI18n();
  const renaming = controls.renamingId === item.id;
  const inputRef = useRef<HTMLInputElement>(null);
  const skipBlur = useRef(false);

  useEffect(() => {
    if (!renaming) return;
    const input = inputRef.current;
    if (!input) return;
    input.focus();
    input.select();
  }, [renaming]);

  if (renaming) {
    return (
      <form
        className="px-1"
        onSubmit={(event) => {
          event.preventDefault();
          controls.onCommitRename(item.id, inputRef.current?.value ?? item.title);
        }}
      >
        <input
          ref={inputRef}
          data-chat="rename-input"
          defaultValue={item.title}
          aria-label={t("chat.rename")}
          className="h-11 w-full rounded-chat-md bg-chat-surface px-3 text-sm text-chat-text outline-none ring-1 ring-chat-accent"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              skipBlur.current = true;
              controls.onCancelRename();
            }
          }}
          onBlur={() => {
            if (skipBlur.current) {
              skipBlur.current = false;
              return;
            }
            controls.onCommitRename(item.id, inputRef.current?.value ?? item.title);
          }}
        />
      </form>
    );
  }

  return (
    <div
      data-chat-row={item.id}
      className={cn(
        "group relative flex items-center gap-0.5 rounded-chat-md",
        active ? "bg-chat-accent-soft" : "hover:bg-chat-surface-secondary",
      )}
    >
      <Link
        href={`/chat/${item.id}`}
        data-chat-item={item.id}
        onClick={onNavigate}
        className={cn(
          "min-w-0 flex-1 rounded-chat-md px-3 py-2.5 text-sm leading-6 text-chat-text",
          active && "font-semibold",
        )}
      >
        <span className="line-clamp-1">{item.title}</span>
      </Link>
      <ConversationOverflowMenu
        item={item}
        open={controls.menuId === item.id}
        onOpen={() => controls.onMenuId(item.id)}
        onClose={() => controls.onMenuId(null)}
        onRename={() => controls.onStartRename(item.id)}
        onPin={() => controls.onPin(item.id)}
        onUnpin={() => controls.onUnpin(item.id)}
        onArchive={() => controls.onArchive(item.id)}
        onShare={() => controls.onShare(item.id)}
        onDelete={() => controls.onRequestDelete(item.id)}
      />
    </div>
  );
}
