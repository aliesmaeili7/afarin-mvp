"use client";

import type { ReactNode } from "react";
import { cn } from "@/components/ui/cn";

export function ChatMenuButton({
  icon,
  label,
  onClick,
  destructive,
  dataChat,
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  destructive?: boolean;
  dataChat?: string;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      data-chat={dataChat}
      data-destructive={destructive ? "true" : undefined}
      onClick={onClick}
      className={cn(
        "flex h-11 w-full items-center gap-3 rounded-chat-md px-3 text-sm font-medium",
        destructive
          ? "text-chat-danger hover:bg-chat-danger/10"
          : "text-chat-text hover:bg-chat-surface-secondary",
      )}
    >
      <span className="grid size-5 place-items-center opacity-80">{icon}</span>
      {label}
    </button>
  );
}
