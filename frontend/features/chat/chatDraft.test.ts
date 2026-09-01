import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearChatDraft, readChatDraft, writeChatDraft } from "./chatDraft";

describe("chat draft", () => {
  const memory: Record<string, string> = {};

  beforeEach(() => {
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => memory[key] ?? null,
      setItem: (key: string, value: string) => {
        memory[key] = value;
      },
      removeItem: (key: string) => {
        delete memory[key];
      },
    });
  });
  afterEach(() => {
    clearChatDraft();
    vi.unstubAllGlobals();
  });

  it("round-trips typed content and theme", () => {
    writeChatDraft({
      content: "سلام",
      themeId: "saved-clay",
      creationAction: "education",
    });
    expect(readChatDraft()).toEqual({
      content: "سلام",
      themeId: "saved-clay",
      creationAction: "education",
    });
  });
});
