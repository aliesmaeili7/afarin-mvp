"use client";

import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { PlusIcon, PanelLeftIcon } from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ConversationSummary } from "@/lib/api/chat/types";
import { ChatAccountRow } from "./ChatAccountRow";
import { sidebarSections } from "./chatHistory";
import type { ConversationControls } from "./history/conversationControls";
import { ConversationList } from "./history/ConversationList";
import { ConversationSearch } from "./history/ConversationSearch";
import { ChatIconButton } from "./primitives/ChatIconButton";

export function ChatSidebar({
  summaries,
  activeId,
  search,
  onSearch,
  collapsed,
  onToggleCollapsed,
  onNavigate,
  controls,
}: {
  summaries: ConversationSummary[];
  activeId: string | null;
  search: string;
  onSearch: (value: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onNavigate?: () => void;
  controls: ConversationControls;
}) {
  const { t } = useI18n();
  const { pinned, groups } = sidebarSections(summaries, search);

  return (
    <aside
      data-chat="sidebar"
      data-collapsed={collapsed ? "true" : "false"}
      className={cn(
        "flex h-full shrink-0 flex-col border-e border-chat-border-subtle bg-chat-bg",
        "chat-motion transition-[width] duration-200 ease-out",
        collapsed ? "w-[72px]" : "w-[276px]",
      )}
    >
      <div className={cn("flex items-center gap-1 px-3 pt-safe", collapsed && "flex-col pt-4")}>
        {collapsed ? (
          <Logo href="/chat" className="h-11" />
        ) : (
          <div className="flex min-w-0 flex-1 items-center">
            <Logo href="/chat" />
          </div>
        )}
        <ChatIconButton
          label={collapsed ? t("chat.expandSidebar") : t("chat.collapseSidebar")}
          data-chat="sidebar-toggle"
          onClick={onToggleCollapsed}
        >
          <PanelLeftIcon width={18} height={18} />
        </ChatIconButton>
      </div>

      <div className={cn("px-3 pt-3", collapsed && "px-2")}>
        <Link
          href="/chat"
          data-chat="new-chat"
          onClick={onNavigate}
          className={cn(
            "flex h-11 items-center gap-2 rounded-full bg-chat-surface text-sm font-semibold text-chat-text shadow-chat-soft",
            collapsed ? "justify-center px-0" : "px-3",
          )}
        >
          <PlusIcon width={16} height={16} />
          {collapsed ? <span className="sr-only">{t("chat.newChat")}</span> : t("chat.newChat")}
        </Link>
      </div>

      {collapsed ? null : (
        <>
          <ConversationSearch value={search} onChange={onSearch} />
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ConversationList
              pinned={pinned}
              groups={groups}
              activeId={activeId}
              onNavigate={onNavigate}
              controls={controls}
            />
          </div>
        </>
      )}

      <ChatAccountRow collapsed={collapsed} onOpenArchive={controls.onOpenArchive} />
    </aside>
  );
}
