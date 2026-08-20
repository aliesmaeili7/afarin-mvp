import type { ReactNode } from "react";
import { cn } from "./cn";
import { CheckIcon } from "./icons";

/** Selectable card used for objective and visual-style steps (spec §8, §9). */
export function ChoiceCard({
  selected,
  onSelect,
  title,
  description,
  media,
  className,
}: {
  selected: boolean;
  onSelect: () => void;
  title: ReactNode;
  description?: ReactNode;
  media?: ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "group relative flex w-full flex-col overflow-hidden rounded-3xl border bg-surface text-start transition-all duration-150",
        "active:scale-[0.99]",
        selected
          ? "border-brand-500 shadow-lift ring-2 ring-brand-200"
          : "border-border shadow-soft hover:border-brand-300",
        className,
      )}
    >
      {media}
      <span className="flex items-start gap-3 p-4">
        <span className="min-w-0 flex-1">
          <span className="block text-base font-bold text-foreground">{title}</span>
          {description ? (
            <span className="mt-1 block text-sm leading-6 text-muted">
              {description}
            </span>
          ) : null}
        </span>
        <span
          className={cn(
            "mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border-2 transition-colors",
            selected
              ? "border-brand-600 bg-brand-600 text-white"
              : "border-ink-200 text-transparent group-hover:border-brand-300",
          )}
          aria-hidden="true"
        >
          <CheckIcon width={14} height={14} strokeWidth={3} />
        </span>
      </span>
    </button>
  );
}
