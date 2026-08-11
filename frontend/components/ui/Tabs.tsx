"use client";

import { cn } from "./cn";

export interface TabItem<T extends string> {
  value: T;
  label: string;
}

export function Tabs<T extends string>({
  items,
  value,
  onChange,
}: {
  items: readonly TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div
      role="tablist"
      className="no-scrollbar flex gap-1 overflow-x-auto rounded-2xl bg-ink-100 p-1"
    >
      {items.map((item) => (
        <button
          key={item.value}
          role="tab"
          type="button"
          aria-selected={value === item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "flex-1 whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition-colors",
            value === item.value
              ? "bg-white text-ink-900 shadow-soft"
              : "text-ink-500 hover:text-ink-800",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
