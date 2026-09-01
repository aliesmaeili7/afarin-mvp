"use client";

import { CloseIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { CREATION_ACTION_CHIPS, type CreationAction } from "./plusMenu";
import { ChatIconButton } from "./primitives/ChatIconButton";

export function CreationActionChip({
  action,
  onRemove,
}: {
  action: CreationAction;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  return (
    <span
      data-chat="action-chip"
      data-action={action}
      className="inline-flex h-9 max-w-full items-center gap-1 rounded-full bg-chat-accent-soft pe-1 ps-3 text-xs font-semibold text-chat-accent"
    >
      <span className="truncate">{t(CREATION_ACTION_CHIPS[action])}</span>
      <ChatIconButton
        label={t("chat.actionRemove")}
        onClick={onRemove}
        className="size-8 text-chat-accent hover:bg-white/40"
      >
        <CloseIcon width={12} height={12} />
      </ChatIconButton>
    </span>
  );
}
