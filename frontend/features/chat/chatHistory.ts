import type { ConversationSummary } from "@/lib/api/chat/types";

export type HistoryGroupId = "today" | "yesterday" | "week" | "older";

export interface HistoryGroup {
  id: HistoryGroupId;
  items: ConversationSummary[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function startOfLocalDay(now = Date.now()): number {
  const date = new Date(now);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

export function historyGroupId(iso: string, now = Date.now()): HistoryGroupId {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return "older";

  const today = startOfLocalDay(now);
  if (time >= today) return "today";
  if (time >= today - DAY_MS) return "yesterday";
  if (time >= today - 7 * DAY_MS) return "week";
  return "older";
}

const GROUP_ORDER: HistoryGroupId[] = ["today", "yesterday", "week", "older"];

export function groupConversations(
  items: ConversationSummary[],
  now = Date.now(),
): HistoryGroup[] {
  const buckets: Record<HistoryGroupId, ConversationSummary[]> = {
    today: [],
    yesterday: [],
    week: [],
    older: [],
  };

  for (const item of items) {
    buckets[historyGroupId(item.updated_at, now)].push(item);
  }

  return GROUP_ORDER.filter((id) => buckets[id].length > 0).map((id) => ({
    id,
    items: buckets[id],
  }));
}

export function filterConversations(
  items: ConversationSummary[],
  query: string,
): ConversationSummary[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return items;
  return items.filter((item) => item.title.toLowerCase().includes(needle));
}

export interface SidebarSections {
  pinned: ConversationSummary[];
  groups: HistoryGroup[];
}

export function sidebarSections(
  items: ConversationSummary[],
  query: string,
  now = Date.now(),
): SidebarSections {
  const visible = filterConversations(
    items.filter((item) => !item.archived),
    query,
  );
  const pinned = visible
    .filter((item) => item.pinned)
    .slice()
    .sort((a, b) =>
      (b.pinned_at ?? b.updated_at).localeCompare(a.pinned_at ?? a.updated_at),
    );
  const unpinned = visible.filter((item) => !item.pinned);
  return { pinned, groups: groupConversations(unpinned, now) };
}
