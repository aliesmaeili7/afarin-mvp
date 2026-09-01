"use client";

import { CloseIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ChatAttachment } from "@/lib/api/chat/types";
import { ChatIconButton } from "./primitives/ChatIconButton";

export function ComposerAttachmentStrip({
  attachment,
  onRemove,
}: {
  attachment: ChatAttachment;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  return (
    <div
      data-chat="attachment-chip"
      className="inline-flex items-center gap-2 rounded-chat-md border border-chat-border-subtle bg-chat-surface pe-1 ps-1.5 py-1"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={attachment.dataUrl}
        alt=""
        width={36}
        height={36}
        className="size-9 rounded-lg object-cover"
      />
      <span className="max-w-32 truncate text-xs text-chat-text">{attachment.name}</span>
      <ChatIconButton
        label={t("chat.attachmentRemove")}
        onClick={onRemove}
        className="size-8"
      >
        <CloseIcon width={12} height={12} />
      </ChatIconButton>
    </div>
  );
}
