"use client";

import type { RewriteIntent } from "@/lib/api/types";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";

const CHIP_KEYS: Record<RewriteIntent, TranslationKey> = {
  informal: "result.rewriteInformal",
  shorter: "result.rewriteShorter",
  more_luxury: "result.rewriteLuxury",
  stronger_cta: "result.rewriteCta",
  new_headline: "result.rewriteHeadline",
};

export const CAPTION_REWRITE_CHIPS: RewriteIntent[] = [
  "informal",
  "shorter",
  "more_luxury",
  "stronger_cta",
];

export const ASSET_REWRITE_CHIPS: RewriteIntent[] = ["new_headline", "stronger_cta"];

export function RewriteChips({
  chips,
  onSelect,
  disabled,
}: {
  chips: RewriteIntent[];
  onSelect: (intent: RewriteIntent) => void;
  disabled?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-bold text-ink-800">{t("result.rewritePrompt")}</p>
      <div className="flex flex-wrap gap-2">
        {chips.map((intent) => (
          <button
            key={intent}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(intent)}
            className="rounded-full border border-ink-200 bg-surface px-3 py-1.5 text-xs font-semibold text-ink-700 hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50"
          >
            {t(CHIP_KEYS[intent])}
          </button>
        ))}
      </div>
    </div>
  );
}
