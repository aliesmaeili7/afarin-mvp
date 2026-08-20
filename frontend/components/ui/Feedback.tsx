"use client";

import type { ReactNode } from "react";
import { cn } from "./cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-2xl bg-[linear-gradient(90deg,var(--color-ink-100)_25%,var(--color-background)_50%,var(--color-ink-100)_75%)] bg-[length:200%_100%]",
        className,
      )}
    />
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-border bg-surface/60 px-6 py-12 text-center">
      {icon ? (
        <div className="grid size-12 place-items-center rounded-2xl bg-brand-50 text-brand-600">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-bold text-foreground">{title}</h3>
      {description ? (
        <p className="max-w-sm text-sm leading-7 text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

/** Friendly, recoverable failure block (Cursor rule 14). */
export function ErrorState({
  title,
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-center gap-3 rounded-3xl border border-coral-300 bg-coral-100/50 px-6 py-10 text-center">
      <span className="text-2xl" aria-hidden="true">
        🙁
      </span>
      <h3 className="text-base font-bold text-foreground">
        {title ?? t("errors.defaultTitle")}
      </h3>
      {description ? (
        <p className="max-w-sm text-sm leading-7 text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
