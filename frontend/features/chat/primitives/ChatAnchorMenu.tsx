"use client";

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { chatChromeDir } from "../chatChrome";
import { useFocusTrap } from "./useFocusTrap";

export function ChatAnchorMenu({
  open,
  onClose,
  anchorRef,
  labelledBy,
  dataChat,
  preferUp,
  children,
}: {
  open: boolean;
  onClose: () => void;
  anchorRef: { current: HTMLElement | null };
  labelledBy?: string;
  dataChat?: string;
  preferUp?: boolean;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const { locale } = useI18n();
  const dir = chatChromeDir(locale);
  useFocusTrap(open, ref, onClose);

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    const width = 260;
    const height = 280;
    let top = preferUp ? rect.top - height - 6 : rect.bottom + 6;
    if (top < 12) top = rect.bottom + 6;
    if (top + height > window.innerHeight - 12) {
      top = Math.max(12, rect.top - height - 6);
    }
    let left = rect.right - width;
    if (left < 8) left = 8;
    if (left + width > window.innerWidth - 8) {
      left = window.innerWidth - width - 8;
    }
    setPos({ top, left });
  }, [open, anchorRef, preferUp]);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: MouseEvent) {
      const target = event.target as Node;
      if (ref.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    }
    const timer = window.setTimeout(() => {
      document.addEventListener("mousedown", onPointer);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open, onClose, anchorRef]);

  if (!open) return null;

  return (
    <div
      ref={ref}
      role="menu"
      aria-labelledby={labelledBy}
      dir={dir}
      data-chat={dataChat}
      data-chat-surface="popover"
      data-chat-dir={dir}
      style={{ top: pos.top, left: pos.left }}
      className={cn(
        "fixed z-[60] min-w-56 overflow-hidden rounded-[24px] bg-chat-surface-elevated p-1.5 shadow-chat-soft",
        "chat-motion animate-[fade-up_180ms_ease-out]",
      )}
    >
      {children}
    </div>
  );
}
