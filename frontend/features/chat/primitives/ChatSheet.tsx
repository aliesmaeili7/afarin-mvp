"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { chatChromeDir } from "../chatChrome";
import { useFocusTrap } from "./useFocusTrap";
import { ChatIconButton } from "./ChatIconButton";
import { CloseIcon } from "@/components/ui/icons";

export function ChatSheet({
  open,
  onClose,
  title,
  children,
  dataChat,
  overlayClassName,
  compact,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  dataChat?: string;
  overlayClassName?: string;
  compact?: boolean;
}) {
  const { t, locale } = useI18n();
  const dir = chatChromeDir(locale);
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(open, ref, onClose);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-end justify-center md:items-center",
        overlayClassName,
      )}
    >
      <button
        type="button"
        aria-label={t("common.close")}
        onClick={onClose}
        className="absolute inset-0 bg-ink-900/30 chat-motion"
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        dir={dir}
        data-chat={dataChat}
        data-chat-surface="sheet"
        data-chat-dir={dir}
        className={cn(
          "relative z-10 flex max-h-[86dvh] w-full max-w-lg flex-col",
          "rounded-t-chat-xl bg-chat-surface shadow-chat-soft md:rounded-chat-xl",
          "chat-motion animate-[fade-up_200ms_ease-out]",
        )}
      >
        <div className="flex items-center justify-between gap-3 px-4 pb-1 pt-4">
          <h2
            className={cn(
              "font-semibold text-chat-text",
              compact ? "text-sm" : "text-base font-bold",
            )}
          >
            {title}
          </h2>
          <ChatIconButton label={t("common.close")} onClick={onClose}>
            <CloseIcon width={18} height={18} />
          </ChatIconButton>
        </div>
        <div className={cn("overflow-y-auto px-4 pb-safe", compact ? "pt-1" : "pt-2")}>
          {children}
        </div>
      </div>
    </div>
  );
}
