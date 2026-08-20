"use client";

import { useEffect, type ReactNode } from "react";
import { Button } from "./Button";
import { CloseIcon } from "./icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

/**
 * Bottom sheet on phones, centred dialog from `sm` up. Used for text editing on
 * the result page so the keyboard never covers the field on mobile.
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { t } = useI18n();
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <button
        type="button"
        aria-label={t("common.close")}
        onClick={onClose}
        className="absolute inset-0 bg-ink-900/45 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative z-10 flex max-h-[88dvh] w-full max-w-lg flex-col rounded-t-3xl bg-surface shadow-lift sm:rounded-3xl"
      >
        <div className="flex items-center justify-between gap-3 border-b border-border p-4">
          <h2 className="text-base font-bold text-foreground">{title}</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label={t("common.close")}
            className="size-11 p-0 sm:size-9"
          >
            <CloseIcon width={18} height={18} />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        {footer ? (
          <div className="border-t border-border p-4 pb-safe">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}
