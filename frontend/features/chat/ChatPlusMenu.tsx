"use client";

import type { ReactNode } from "react";
import {
  ImageIcon,
  PaletteIcon,
  UploadIcon,
} from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { ChatPopover } from "./primitives/ChatPopover";
import { ChatSheet } from "./primitives/ChatSheet";
import {
  PLUS_MENU_ITEMS,
  isCreationAction,
  type CreationAction,
  type PlusMenuId,
} from "./plusMenu";

export function ChatPlusMenu({
  open,
  onClose,
  sheet,
  onSelectCreation,
  onUpload,
  onTheme,
}: {
  open: boolean;
  onClose: () => void;
  sheet: boolean;
  onSelectCreation: (action: CreationAction) => void;
  onUpload: () => void;
  onTheme: () => void;
}) {
  const { t } = useI18n();

  function handle(id: PlusMenuId) {
    if (isCreationAction(id)) {
      onSelectCreation(id);
    } else if (id === "upload") {
      onUpload();
    } else {
      onTheme();
    }
    onClose();
  }

  const items = (
    <div className="flex flex-col gap-1">
      {PLUS_MENU_ITEMS.map((item) => (
        <MenuItem
          key={item.id}
          icon={menuIcon(item.id)}
          label={t(item.labelKey)}
          action={item.action}
          onClick={() => handle(item.id)}
        />
      ))}
    </div>
  );

  if (sheet) {
    return (
      <ChatSheet open={open} onClose={onClose} title={t("chat.plusMenu")}>
        <div data-chat="plus-menu" className="pb-4">
          {items}
        </div>
      </ChatSheet>
    );
  }

  return (
    <ChatPopover open={open} onClose={onClose}>
      {items}
    </ChatPopover>
  );
}

function menuIcon(id: PlusMenuId): ReactNode {
  if (id === "advertising") return <span aria-hidden="true">📣</span>;
  if (id === "education") return <span aria-hidden="true">🎓</span>;
  if (id === "general_image") return <ImageIcon width={18} height={18} />;
  if (id === "upload") return <UploadIcon width={18} height={18} />;
  return <PaletteIcon width={18} height={18} />;
}

function MenuItem({
  icon,
  label,
  action,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  action: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      data-chat-action={action}
      onClick={onClick}
      className="flex h-12 w-full items-center gap-3 rounded-chat-md px-3 text-sm font-medium text-chat-text hover:bg-chat-surface-secondary"
    >
      <span className="grid size-5 place-items-center text-chat-text-secondary">
        {icon}
      </span>
      {label}
    </button>
  );
}
