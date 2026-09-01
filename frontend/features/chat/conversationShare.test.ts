import { describe, expect, it } from "vitest";
import {
  formatConversationShareText,
  shareSheetOptions,
} from "./conversationShare";
import type { Conversation } from "@/lib/api/chat/types";

function conversation(): Conversation {
  return {
    id: "c1",
    title: "اعشار",
    language: "fa",
    active_theme_id: null,
    pinned: false,
    archived: false,
    pinned_at: null,
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    messages: [
      {
        id: "m1",
        conversation_id: "c1",
        role: "user",
        content: "یه پست بساز",
        language: "fa",
        created_at: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "m2",
        conversation_id: "c1",
        role: "assistant",
        content: "باشه",
        language: "fa",
        created_at: "2026-01-01T00:00:01.000Z",
      },
    ],
    artifacts: [],
  };
}

describe("conversation share text", () => {
  it("formats a copyable transcript without a URL", () => {
    const text = formatConversationShareText(conversation());
    expect(text).toContain("اعشار");
    expect(text).toContain("شما: یه پست بساز");
    expect(text).toContain("آفرین: باشه");
    expect(text).not.toMatch(/https?:\/\//);
  });

  it("never offers a public link when none exists", () => {
    expect(shareSheetOptions(null, false)).toEqual(["copyText"]);
    expect(shareSheetOptions(null, true)).toEqual(["copyText", "native"]);
    expect(shareSheetOptions(null, true)).not.toContain("copyLink");
    expect(shareSheetOptions("https://example.com/s/abc", false)).toContain(
      "copyLink",
    );
  });
});
