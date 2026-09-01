"use client";

import { MenuIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { ChatIconButton } from "./primitives/ChatIconButton";

export function ChatTopBar({
  title,
  onOpenSidebar,
}: {
  title: string;
  onOpenSidebar: () => void;
}) {
  const { t } = useI18n();
  return (
    <header className="flex h-14 shrink-0 items-center gap-1 border-b border-transparent px-2 pt-safe md:hidden">
      <ChatIconButton label={t("chat.openSidebar")} onClick={onOpenSidebar} data-chat="open-sidebar">
        <MenuIcon width={20} height={20} />
      </ChatIconButton>
      <h1 className="min-w-0 flex-1 truncate text-center text-sm font-semibold text-chat-text">
        {title}
      </h1>
      <span className="size-11" aria-hidden="true" />
    </header>
  );
}
