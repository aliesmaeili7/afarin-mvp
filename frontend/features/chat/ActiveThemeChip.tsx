"use client";

import { CloseIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ChatTheme } from "@/lib/api/chat/types";
import { ChatIconButton } from "./primitives/ChatIconButton";

export function ActiveThemeChip({
  theme,
  onRemove,
}: {
  theme: ChatTheme;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  return (
    <span
      data-chat="theme-chip"
      className="inline-flex h-9 max-w-full items-center gap-2 rounded-full bg-chat-accent-soft pe-1 ps-2.5 text-xs font-semibold text-chat-accent"
    >
      <span
        className="size-3.5 shrink-0 rounded-full"
        style={{ background: theme.swatch }}
        aria-hidden="true"
      />
      <span className="truncate">{theme.name}</span>
      <ChatIconButton
        label={t("chat.themeRemove")}
        onClick={onRemove}
        className="size-8 text-chat-accent hover:bg-white/40"
      >
        <CloseIcon width={12} height={12} />
      </ChatIconButton>
    </span>
  );
}
