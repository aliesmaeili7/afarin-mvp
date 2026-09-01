"use client";

import { useRef } from "react";
import {
  ArchiveIcon,
  MoreIcon,
  PinIcon,
  ShareIcon,
  TrashIcon,
} from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { ConversationSummary } from "@/lib/api/chat/types";
import { overflowActions, isDestructiveMenuAction } from "../conversationActions";
import { chatMenuSurface } from "../chatChrome";
import { ChatAnchorMenu } from "../primitives/ChatAnchorMenu";
import { ChatMenuButton } from "../primitives/ChatMenuButton";
import { ChatSheet } from "../primitives/ChatSheet";
import { useMobileSheet } from "../useChatSession";

export function ConversationOverflowMenu({
  item,
  open,
  onOpen,
  onClose,
  onRename,
  onPin,
  onUnpin,
  onArchive,
  onShare,
  onDelete,
}: {
  item: ConversationSummary;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  onRename: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onArchive: () => void;
  onShare: () => void;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  const mobile = useMobileSheet();
  const surface = chatMenuSurface(mobile);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const actions = overflowActions(item.pinned);

  function run(action: () => void) {
    onClose();
    action();
  }

  const items = (
    <div className="flex flex-col gap-0.5">
      {actions.map((action) => {
        if (action === "rename") {
          return (
            <ChatMenuButton
              key={action}
              dataChat="conv-rename"
              icon={<span className="text-sm font-bold">Aa</span>}
              label={t("chat.rename")}
              onClick={() => run(onRename)}
            />
          );
        }
        if (action === "pin") {
          return (
            <ChatMenuButton
              key={action}
              dataChat="conv-pin"
              icon={<PinIcon width={18} height={18} />}
              label={t("chat.pin")}
              onClick={() => run(onPin)}
            />
          );
        }
        if (action === "unpin") {
          return (
            <ChatMenuButton
              key={action}
              dataChat="conv-unpin"
              icon={<PinIcon width={18} height={18} />}
              label={t("chat.unpin")}
              onClick={() => run(onUnpin)}
            />
          );
        }
        if (action === "archive") {
          return (
            <ChatMenuButton
              key={action}
              dataChat="conv-archive"
              icon={<ArchiveIcon width={18} height={18} />}
              label={t("chat.archive")}
              onClick={() => run(onArchive)}
            />
          );
        }
        if (action === "share") {
          return (
            <ChatMenuButton
              key={action}
              dataChat="conv-share"
              icon={<ShareIcon width={18} height={18} />}
              label={t("chat.share")}
              onClick={() => run(onShare)}
            />
          );
        }
        return (
          <ChatMenuButton
            key={action}
            dataChat="conv-delete"
            icon={<TrashIcon width={18} height={18} />}
            label={t("chat.delete")}
            destructive={isDestructiveMenuAction(action)}
            onClick={() => run(onDelete)}
          />
        );
      })}
    </div>
  );

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        data-chat="conversation-menu-btn"
        aria-label={t("chat.conversationMenu")}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (open) onClose();
          else onOpen();
        }}
        className={cn(
          "grid size-9 shrink-0 place-items-center rounded-full text-chat-text-secondary",
          "opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100",
          "hover:bg-chat-surface-secondary hover:text-chat-text",
          open && "opacity-100 bg-chat-surface-secondary",
        )}
      >
        <MoreIcon width={16} height={16} />
      </button>
      {surface === "sheet" ? (
        <ChatSheet
          open={open}
          onClose={onClose}
          title={item.title}
          dataChat="conversation-menu"
          overlayClassName="z-[60]"
          compact
        >
          <div className="pb-3">{items}</div>
        </ChatSheet>
      ) : (
        <ChatAnchorMenu
          open={open}
          onClose={onClose}
          anchorRef={buttonRef}
          dataChat="conversation-menu"
        >
          {items}
        </ChatAnchorMenu>
      )}
    </>
  );
}
