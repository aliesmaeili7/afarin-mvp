"use client";

import type {
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";
import { useId } from "react";
import { cn } from "./cn";

const CONTROL_CLASSES =
  "w-full rounded-2xl border border-ink-200 bg-white px-4 py-3 text-[0.95rem] text-ink-900 " +
  "placeholder:text-ink-300 transition-colors focus:border-brand-400 focus:outline-none " +
  "focus:ring-4 focus:ring-brand-100 disabled:bg-ink-50";

function Label({
  htmlFor,
  children,
  optional,
}: {
  htmlFor: string;
  children: ReactNode;
  optional?: boolean;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="flex items-center gap-2 text-sm font-semibold text-ink-800"
    >
      {children}
      {optional ? (
        <span className="text-xs font-normal text-ink-400">(اختیاری)</span>
      ) : null}
    </label>
  );
}

function Hint({ hint, error }: { hint?: ReactNode; error?: string | null }) {
  if (error) {
    return <p className="text-xs font-medium text-coral-600">{error}</p>;
  }
  if (!hint) return null;
  return <p className="text-xs leading-6 text-ink-400">{hint}</p>;
}

export interface TextFieldProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  optional?: boolean;
  trailing?: ReactNode;
}

export function TextField({
  label,
  hint,
  error,
  optional,
  trailing,
  className,
  ...props
}: TextFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id} optional={optional}>
        {label}
      </Label>
      <div className="relative">
        <input
          {...props}
          id={id}
          className={cn(
            CONTROL_CLASSES,
            error && "border-coral-300 focus:border-coral-500 focus:ring-coral-100",
            trailing ? "pe-12" : null,
            className,
          )}
        />
        {trailing ? (
          <div className="absolute inset-y-0 end-3 flex items-center">{trailing}</div>
        ) : null}
      </div>
      <Hint hint={hint} error={error} />
    </div>
  );
}

export interface TextAreaFieldProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  optional?: boolean;
}

export function TextAreaField({
  label,
  hint,
  error,
  optional,
  className,
  rows = 3,
  ...props
}: TextAreaFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id} optional={optional}>
        {label}
      </Label>
      <textarea
        {...props}
        id={id}
        rows={rows}
        className={cn(
          CONTROL_CLASSES,
          "resize-none leading-8",
          error && "border-coral-300 focus:border-coral-500 focus:ring-coral-100",
          className,
        )}
      />
      <Hint hint={hint} error={error} />
    </div>
  );
}

/** Tappable suggestion pills used instead of empty prompt boxes (spec §5.4). */
export function SuggestionChips({
  items,
  onSelect,
  activeItem,
}: {
  items: readonly string[];
  onSelect: (value: string) => void;
  activeItem?: string | null;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onSelect(item)}
          className={cn(
            "flex h-11 items-center rounded-full border px-3.5 text-sm transition-colors sm:h-9",
            activeItem === item
              ? "border-brand-400 bg-brand-50 text-brand-700"
              : "border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-brand-700",
          )}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
