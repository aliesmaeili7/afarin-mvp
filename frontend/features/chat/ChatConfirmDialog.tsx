"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/components/ui/cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { chatChromeDir } from "./chatChrome";
import { useFocusTrap } from "./primitives/useFocusTrap";

export function ChatConfirmDialog({
  open,
  onClose,
  title,
  body,
  confirmLabel,
  onConfirm,
  destructive,
  dataChat,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  destructive?: boolean;
  dataChat?: string;
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
    <div className="fixed inset-0 z-[70] flex items-end justify-center p-3 md:items-center">
      <button
        type="button"
        aria-label={t("common.close")}
        onClick={onClose}
        className="absolute inset-0 bg-ink-900/30"
      />
      <div
        ref={ref}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="chat-confirm-title"
        dir={dir}
        data-chat={dataChat}
        data-chat-surface="sheet"
        data-chat-dir={dir}
        data-destructive={destructive ? "true" : undefined}
        className="relative z-10 w-full max-w-sm rounded-[24px] bg-chat-surface-elevated p-5 shadow-chat-soft"
      >
        <h2
          id="chat-confirm-title"
          className="text-base font-bold text-chat-text"
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-chat-text-secondary">{body}</p>
        <div className="mt-5 flex gap-2">
          <button
            type="button"
            data-chat="confirm-cancel"
            onClick={onClose}
            className="h-11 flex-1 rounded-full bg-chat-surface-secondary text-sm font-semibold text-chat-text"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            data-chat="confirm-ok"
            data-destructive={destructive ? "true" : undefined}
            onClick={onConfirm}
            className={cn(
              "h-11 flex-1 rounded-full text-sm font-semibold text-white",
              destructive ? "bg-chat-danger" : "bg-chat-accent",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
