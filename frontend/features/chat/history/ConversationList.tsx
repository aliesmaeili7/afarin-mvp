"use client";

import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import type { ConversationSummary } from "@/lib/api/chat/types";
import type { HistoryGroup } from "../chatHistory";
import type { ConversationControls } from "./conversationControls";
import { ConversationListItem } from "./ConversationListItem";

const GROUP_KEYS: Record<HistoryGroup["id"], TranslationKey> = {
  today: "chat.groupToday",
  yesterday: "chat.groupYesterday",
  week: "chat.groupWeek",
  older: "chat.groupOlder",
};

export function ConversationList({
  pinned,
  groups,
  activeId,
  onNavigate,
  controls,
}: {
  pinned: ConversationSummary[];
  groups: HistoryGroup[];
  activeId: string | null;
  onNavigate?: () => void;
  controls: ConversationControls;
}) {
  const { t } = useI18n();

  if (pinned.length === 0 && groups.length === 0) {
    return (
      <p className="px-4 py-6 text-sm text-chat-text-secondary">
        {t("chat.noResults")}
      </p>
    );
  }

  return (
    <nav className="flex flex-col gap-5 px-2 py-3" aria-label={t("chat.search")}>
      {pinned.length > 0 ? (
        <section data-chat="group-pinned">
          <h2 className="px-3 pb-1 text-xs font-semibold text-chat-text-secondary">
            {t("chat.groupPinned")}
          </h2>
          <div className="flex flex-col gap-0.5">
            {pinned.map((item) => (
              <ConversationListItem
                key={item.id}
                item={item}
                active={item.id === activeId}
                onNavigate={onNavigate}
                controls={controls}
              />
            ))}
          </div>
        </section>
      ) : null}
      {groups.map((group) => (
        <section key={group.id}>
          <h2 className="px-3 pb-1 text-xs font-semibold text-chat-text-secondary">
            {t(GROUP_KEYS[group.id])}
          </h2>
          <div className="flex flex-col gap-0.5">
            {group.items.map((item) => (
              <ConversationListItem
                key={item.id}
                item={item}
                active={item.id === activeId}
                onNavigate={onNavigate}
                controls={controls}
              />
            ))}
          </div>
        </section>
      ))}
    </nav>
  );
}
