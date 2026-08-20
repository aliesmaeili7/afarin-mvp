"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "subtle";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground shadow-soft hover:bg-brand-700 active:bg-brand-800 disabled:bg-ink-200 disabled:text-muted disabled:shadow-none",
  secondary:
    "bg-foreground text-background shadow-soft hover:opacity-90 disabled:bg-ink-200 disabled:text-muted disabled:shadow-none disabled:opacity-100",
  outline:
    "border border-border bg-surface text-foreground hover:border-brand-300 hover:bg-brand-50 disabled:text-muted",
  ghost: "text-muted hover:bg-ink-100 hover:text-foreground disabled:text-muted",
  subtle:
    "bg-brand-50 text-brand-700 hover:bg-brand-100 active:bg-brand-200 disabled:text-brand-300",
};

/**
 * Small buttons stay a comfortable 44px touch target on phones and only shrink
 * once there is a pointer, so header and inline controls remain thumb-friendly.
 */
const SIZES: Record<Size, string> = {
  sm: "h-11 sm:h-9 px-3.5 text-sm gap-1.5 rounded-xl",
  md: "h-11 px-5 text-[0.95rem] gap-2 rounded-2xl",
  lg: "h-13 px-6 text-base gap-2.5 rounded-2xl",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
  loading?: boolean;
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  fullWidth,
  loading,
  iconStart,
  iconEnd,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn(
        "inline-flex select-none items-center justify-center font-semibold transition-all duration-150",
        "disabled:cursor-not-allowed active:scale-[0.99]",
        VARIANTS[variant],
        SIZES[size],
        fullWidth && "w-full",
        className,
      )}
    >
      {loading ? <Spinner /> : iconStart}
      <span className="truncate">{children}</span>
      {!loading && iconEnd}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <span
      className={cn(
        "size-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
      role="status"
      aria-label={t("common.loading")}
    />
  );
}
