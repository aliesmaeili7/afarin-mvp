"use client";

import type { RewriteIntent } from "@/lib/api/types";

export interface RewriteChip {
  intent: RewriteIntent;
  label: string;
}

export const CAPTION_REWRITE_CHIPS: RewriteChip[] = [
  { intent: "informal", label: "کپشن رو خودمونی‌تر کن" },
  { intent: "shorter", label: "متن رو کوتاه‌تر کن" },
  { intent: "more_luxury", label: "تبلیغ رو لوکس‌تر کن" },
  { intent: "stronger_cta", label: "CTA قوی‌تر بده" },
];

export const ASSET_REWRITE_CHIPS: RewriteChip[] = [
  { intent: "new_headline", label: "یه تیتر جدید بده" },
  { intent: "stronger_cta", label: "CTA قوی‌تر بده" },
];

export function RewriteChips({
  chips,
  onSelect,
  disabled,
}: {
  chips: RewriteChip[];
  onSelect: (intent: RewriteIntent) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-bold text-ink-800">چی رو می‌خوای تغییر بدی؟</p>
      <div className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <button
            key={chip.intent}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(chip.intent)}
            className="rounded-full border border-ink-200 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50"
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}
