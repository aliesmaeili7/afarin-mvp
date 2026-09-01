"use client";

import { useEffect, useState } from "react";
import { CopyIcon, ShareIcon } from "@/components/ui/icons";
import { chatApi } from "@/lib/api/chat";
import type { ConversationSharePayload } from "@/lib/api/chat/types";
import { useClipboard } from "@/lib/hooks/useClipboard";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { canShareNatively, shareSheetOptions } from "./conversationShare";
import { ChatMenuButton } from "./primitives/ChatMenuButton";
import { ChatSheet } from "./primitives/ChatSheet";

export function ChatShareSheet({
  conversationId,
  onClose,
}: {
  conversationId: string | null;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const copy = useClipboard();
  const [payload, setPayload] = useState<{
    id: string;
    data: ConversationSharePayload;
  } | null>(null);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    void chatApi.shareConversation(conversationId).then(
      (data) => {
        if (!cancelled) setPayload({ id: conversationId, data });
      },
      () => {
        if (!cancelled) setPayload(null);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  const current = payload?.id === conversationId ? payload.data : null;
  const native = canShareNatively();
  const options = shareSheetOptions(current?.publicUrl ?? null, native);

  async function handleCopy() {
    if (!current) return;
    await copy(current.text);
    onClose();
  }

  async function handleNative() {
    if (!current || !native) return;
    try {
      await navigator.share({ title: current.title, text: current.text });
      onClose();
    } catch {
      // User cancelled the sheet; stay open.
    }
  }

  return (
    <ChatSheet
      open={Boolean(conversationId)}
      onClose={onClose}
      title={t("chat.share")}
      dataChat="share-sheet"
      overlayClassName="z-[60]"
      compact
    >
      <div className="flex flex-col gap-1 pb-4">
        {options.includes("copyText") ? (
          <ChatMenuButton
            icon={<CopyIcon width={18} height={18} />}
            label={t("chat.shareCopyText")}
            dataChat="share-copy"
            onClick={() => void handleCopy()}
          />
        ) : null}
        {options.includes("native") ? (
          <ChatMenuButton
            icon={<ShareIcon width={18} height={18} />}
            label={t("chat.shareSystem")}
            dataChat="share-native"
            onClick={() => void handleNative()}
          />
        ) : null}
        <p className="px-3 pt-3 text-xs leading-5 text-chat-text-secondary">
          {t("chat.shareNoLink")}
        </p>
      </div>
    </ChatSheet>
  );
}
