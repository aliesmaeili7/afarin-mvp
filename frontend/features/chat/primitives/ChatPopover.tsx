"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/components/ui/cn";
import { useFocusTrap } from "./useFocusTrap";

export function ChatPopover({
  open,
  onClose,
  labelledBy,
  className,
  dataChat = "plus-menu",
  ignoreRef,
  children,
}: {
  open: boolean;
  onClose: () => void;
  labelledBy?: string;
  className?: string;
  dataChat?: string;
  ignoreRef?: { current: HTMLElement | null };
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(open, ref, onClose);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: MouseEvent) {
      const target = event.target as Node;
      if (ref.current?.contains(target)) return;
      if (ignoreRef?.current?.contains(target)) return;
      onClose();
    }
    const timer = window.setTimeout(() => {
      document.addEventListener("mousedown", onPointer);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open, onClose, ignoreRef]);

  if (!open) return null;

  return (
    <div
      ref={ref}
      role="menu"
      aria-labelledby={labelledBy}
      data-chat={dataChat}
      className={cn(
        "absolute bottom-[calc(100%+10px)] start-0 z-30 min-w-56 origin-bottom overflow-hidden rounded-chat-lg",
        "bg-chat-surface-elevated p-1.5 shadow-chat-soft",
        "chat-motion animate-[fade-up_180ms_ease-out]",
        className,
      )}
    >
      {children}
    </div>
  );
}
