import { describe, expect, it } from "vitest";
import {
  deleteRequiresConfirmation,
  isDestructiveMenuAction,
  overflowActions,
  shouldLeaveConversation,
} from "./conversationActions";
import { sidebarSections } from "./chatHistory";
import type { ConversationSummary } from "@/lib/api/chat/types";

function summary(
  id: string,
  extra: Partial<ConversationSummary> = {},
): ConversationSummary {
  const now = "2026-09-01T15:00:00.000Z";
  return {
    id,
    title: id,
    language: "fa",
    active_theme_id: null,
    pinned: false,
    archived: false,
    pinned_at: null,
    created_at: now,
    updated_at: now,
    ...extra,
  };
}

describe("conversation actions", () => {
  it("exposes rename, pin, archive, share, and delete", () => {
    expect(overflowActions(false)).toEqual([
      "rename",
      "pin",
      "archive",
      "share",
      "delete",
    ]);
    expect(overflowActions(true)).toEqual([
      "rename",
      "unpin",
      "archive",
      "share",
      "delete",
    ]);
    expect(overflowActions(false).join(",")).not.toMatch(/project/i);
  });

  it("marks delete as the only destructive action", () => {
    expect(isDestructiveMenuAction("delete")).toBe(true);
    expect(isDestructiveMenuAction("archive")).toBe(false);
    expect(deleteRequiresConfirmation()).toBe(true);
  });

  it("leaves the current chat after deleting it", () => {
    expect(shouldLeaveConversation("a", "a")).toBe(true);
    expect(shouldLeaveConversation("a", "b")).toBe(false);
    expect(shouldLeaveConversation("a", null)).toBe(false);
  });

  it("moves pinned chats into the pinned group", () => {
    const now = Date.parse("2026-09-01T15:00:00");
    const afterPin = sidebarSections(
      [
        summary("open", { pinned: false }),
        summary("pinned", {
          pinned: true,
          pinned_at: "2026-09-01T16:00:00.000Z",
        }),
      ],
      "",
      now,
    );
    expect(afterPin.pinned.map((item) => item.id)).toEqual(["pinned"]);
    expect(afterPin.groups.flatMap((group) => group.items).map((item) => item.id)).toEqual(
      ["open"],
    );
  });
});
