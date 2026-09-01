"use client";

import { cn } from "@/components/ui/cn";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function ChatIconButton({
  label,
  active,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  active?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      className={cn(
        "grid size-11 shrink-0 place-items-center rounded-full text-chat-text-secondary",
        "transition-colors duration-200 ease-out chat-motion",
        "hover:bg-chat-surface-secondary hover:text-chat-text",
        "disabled:pointer-events-none disabled:opacity-40",
        active && "bg-chat-accent-soft text-chat-accent",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
