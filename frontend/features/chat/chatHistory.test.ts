import { describe, expect, it } from "vitest";
import {
  filterConversations,
  groupConversations,
  historyGroupId,
  sidebarSections,
  startOfLocalDay,
} from "./chatHistory";
import type { ConversationSummary } from "@/lib/api/chat/types";

function summary(
  id: string,
  updatedAt: string,
  title = id,
  extra: Partial<ConversationSummary> = {},
): ConversationSummary {
  return {
    id,
    title,
    language: "fa",
    active_theme_id: null,
    pinned: false,
    archived: false,
    pinned_at: null,
    created_at: updatedAt,
    updated_at: updatedAt,
    ...extra,
  };
}

describe("history grouping", () => {
  const now = Date.parse("2026-09-01T15:00:00");
  const todayStart = startOfLocalDay(now);

  it("buckets by today, yesterday, week, and older", () => {
    expect(historyGroupId(new Date(now).toISOString(), now)).toBe("today");
    expect(
      historyGroupId(new Date(todayStart - 2 * 60 * 60 * 1000).toISOString(), now),
    ).toBe("yesterday");
    expect(
      historyGroupId(new Date(todayStart - 3 * 24 * 60 * 60 * 1000).toISOString(), now),
    ).toBe("week");
    expect(
      historyGroupId(new Date(todayStart - 20 * 24 * 60 * 60 * 1000).toISOString(), now),
    ).toBe("older");
  });

  it("omits empty groups and preserves order", () => {
    const groups = groupConversations(
      [
        summary("a", new Date(now).toISOString()),
        summary("b", new Date(todayStart - 20 * 24 * 60 * 60 * 1000).toISOString()),
      ],
      now,
    );
    expect(groups.map((group) => group.id)).toEqual(["today", "older"]);
  });

  it("filters titles", () => {
    const items = [
      summary("1", new Date(now).toISOString(), "تبلیغ کفش سفید"),
      summary("2", new Date(now).toISOString(), "ماموریت ممیز کوچولو"),
    ];
    expect(filterConversations(items, "کفش").map((item) => item.id)).toEqual([
      "1",
    ]);
    expect(filterConversations(items, "  ")).toHaveLength(2);
  });

  it("keeps pinned chats in a top group and out of date buckets", () => {
    const nowIso = new Date(now).toISOString();
    const olderIso = new Date(todayStart - 20 * 24 * 60 * 60 * 1000).toISOString();
    const sections = sidebarSections(
      [
        summary("pinned-today", nowIso, "سنجاق", {
          pinned: true,
          pinned_at: nowIso,
        }),
        summary("today", nowIso, "امروز"),
        summary("archived", olderIso, "بایگانی", { archived: true }),
      ],
      "",
      now,
    );
    expect(sections.pinned.map((item) => item.id)).toEqual(["pinned-today"]);
    expect(sections.groups.map((group) => group.id)).toEqual(["today"]);
    expect(sections.groups[0]?.items.map((item) => item.id)).toEqual(["today"]);
  });
});
