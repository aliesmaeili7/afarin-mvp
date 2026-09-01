"use client";

import { SearchIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

export function ConversationSearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useI18n();
  return (
    <label className="relative mx-3 mt-2 block">
      <span className="sr-only">{t("chat.search")}</span>
      <SearchIcon
        width={16}
        height={16}
        className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-chat-text-secondary"
      />
      <input
        data-chat="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("chat.searchPlaceholder")}
        className="h-11 w-full rounded-full border border-chat-border-subtle bg-chat-surface-secondary ps-9 pe-3 text-sm text-chat-text outline-none placeholder:text-chat-text-secondary focus:border-chat-accent"
      />
    </label>
  );
}
