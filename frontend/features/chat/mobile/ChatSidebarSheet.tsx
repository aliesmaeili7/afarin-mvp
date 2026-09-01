"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { useFocusTrap } from "../primitives/useFocusTrap";
import { ChatSidebar } from "../ChatSidebar";
import type { ConversationControls } from "../history/conversationControls";
import type { ConversationSummary } from "@/lib/api/chat/types";

export function ChatSidebarSheet({
  open,
  onClose,
  summaries,
  activeId,
  search,
  onSearch,
  controls,
  listLoading,
  listError,
  onRetryList,
}: {
  open: boolean;
  onClose: () => void;
  summaries: ConversationSummary[];
  activeId: string | null;
  search: string;
  onSearch: (value: string) => void;
  controls: ConversationControls;
  listLoading?: boolean;
  listError?: boolean;
  onRetryList?: () => void;
}) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(open, ref, onClose);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <button
        type="button"
        aria-label={t("chat.closeSidebar")}
        className="absolute inset-0 bg-ink-900/40"
        onClick={onClose}
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={t("chat.openSidebar")}
        data-chat="sidebar-sheet"
        className={cn(
          "absolute inset-y-0 start-0 w-[min(86vw,276px)] bg-chat-bg shadow-chat-soft",
          "chat-motion animate-[fade-up_200ms_ease-out]",
        )}
      >
        <ChatSidebar
          summaries={summaries}
          activeId={activeId}
          search={search}
          onSearch={onSearch}
          collapsed={false}
          onToggleCollapsed={onClose}
          onNavigate={onClose}
          controls={controls}
          listLoading={listLoading}
          listError={listError}
          onRetryList={onRetryList}
        />
      </div>
    </div>
  );
}
