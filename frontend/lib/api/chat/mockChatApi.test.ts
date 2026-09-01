import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { chatApi } from "./index";
import {
  resetChatMock,
  restoreChatMockDelay,
} from "./mockChatApi";

describe("mock ChatApi", () => {
  beforeEach(() => {
    resetChatMock();
  });

  afterEach(() => {
    restoreChatMockDelay();
  });

  it("lists seeded conversations", async () => {
    const list = await chatApi.listConversations();
    expect(list.some((item) => item.id === "conv-decimals")).toBe(true);
    expect(list.some((item) => item.id === "conv-shoe")).toBe(true);
    expect(list.some((item) => item.id === "conv-english")).toBe(true);
  });

  it("loads a conversation with a 1:1 artifact", async () => {
    const conversation = await chatApi.getConversation("conv-decimals");
    expect(conversation.artifacts[0]?.aspect_ratio).toBe("1:1");
    expect(conversation.messages.some((item) => item.role === "user")).toBe(
      true,
    );
  });

  it("loads a 4:5 advertising artifact", async () => {
    const conversation = await chatApi.getConversation("conv-shoe");
    expect(conversation.artifacts[0]?.aspect_ratio).toBe("4:5");
  });

  it("creates, sends, and titles a conversation", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
    });
    expect(conversation.messages).toHaveLength(2);
    expect(conversation.artifacts.length).toBeGreaterThan(0);
    expect(conversation.title).toContain("کلاس");
    const list = await chatApi.listConversations();
    expect(list[0]?.id).toBe(created.id);
  });

  it("does not generate from an attachment-only send", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "",
      attachment: { name: "shoe.jpg", dataUrl: "data:image/png;base64,aaa" },
    });
    expect(conversation.messages[0]?.metadata_json?.attachment?.name).toBe(
      "shoe.jpg",
    );
    expect(conversation.artifacts).toHaveLength(0);
  });

  it("sets and clears the active theme", async () => {
    const created = await chatApi.createConversation();
    const themed = await chatApi.setActiveTheme(created.id, "saved-clay");
    expect(themed.active_theme?.id).toBe("saved-clay");
    const cleared = await chatApi.setActiveTheme(created.id, null);
    expect(cleared.active_theme).toBeNull();
  });

  it("generateImage produces a ready artifact", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.generateImage(created.id);
    expect(conversation.artifacts[0]?.status).toBe("ready");
    expect(conversation.artifacts[0]?.storage_path).toContain("mock/chat");
  });

  it("replies in English when the user writes English", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "Make an elegant Instagram ad for this shoe.",
    });
    const assistant = conversation.messages.find(
      (item) => item.role === "assistant",
    );
    expect(assistant?.language).toBe("en");
  });

  it("does not auto-generate a caption-only request", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "برای این عکس یه کپشن دوستانه بنویس",
    });
    expect(conversation.artifacts).toHaveLength(0);
  });

  it("uses an advertising skill hint without requiring generateImage", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "برای این کفش",
      skillHint: "advertising",
    });
    expect(conversation.artifacts[0]?.aspect_ratio).toBe("4:5");
  });

  it("uses an education skill hint for a square post", async () => {
    const created = await chatApi.createConversation();
    const { conversation } = await chatApi.sendMessage(created.id, {
      content: "اعداد اعشاری",
      skillHint: "education",
    });
    expect(conversation.artifacts[0]?.aspect_ratio).toBe("1:1");
  });

  it("hides archived chats from the main list", async () => {
    const list = await chatApi.listConversations();
    expect(list.some((item) => item.id === "conv-failed")).toBe(false);
    const archived = await chatApi.listArchivedConversations();
    expect(archived.some((item) => item.id === "conv-failed")).toBe(true);
  });

  it("pins a conversation without duplicating it in the open list", async () => {
    const pinned = await chatApi.pinConversation("conv-shoe");
    expect(pinned.pinned).toBe(true);
    const list = await chatApi.listConversations();
    expect(list.filter((item) => item.id === "conv-shoe")).toHaveLength(1);
    const unpinned = await chatApi.unpinConversation("conv-shoe");
    expect(unpinned.pinned).toBe(false);
  });

  it("renames, archives, restores, and deletes", async () => {
    const created = await chatApi.createConversation();
    const renamed = await chatApi.renameConversation(created.id, "کلاس ریاضی");
    expect(renamed.title).toBe("کلاس ریاضی");
    await chatApi.archiveConversation(created.id);
    expect(
      (await chatApi.listConversations()).some((item) => item.id === created.id),
    ).toBe(false);
    await chatApi.restoreConversation(created.id);
    expect(
      (await chatApi.listConversations()).some((item) => item.id === created.id),
    ).toBe(true);
    await chatApi.deleteConversation(created.id);
    await expect(chatApi.getConversation(created.id)).rejects.toThrow(
      "conversation_not_found",
    );
  });

  it("creates a conversation on first send without a prior create call", async () => {
    const { conversation } = await chatApi.sendMessage(null, {
      content: "سلام آفرین",
    });
    expect(conversation.messages[0]?.role).toBe("user");
    expect(conversation.title).toContain("سلام");
  });

  it("searches titles", async () => {
    const found = await chatApi.searchConversations("کفش");
    expect(found.some((item) => item.id === "conv-shoe")).toBe(true);
    expect(found.some((item) => item.id === "conv-decimals")).toBe(false);
  });

  it("shares conversation text without a public URL", async () => {
    const share = await chatApi.shareConversation("conv-decimals");
    expect(share.publicUrl).toBeNull();
    expect(share.text).toContain("ماموریت ممیز کوچولو");
    expect(share.text).toContain("شما:");
    expect(share.text).toContain("آفرین:");
  });

  it("ignores a blank rename", async () => {
    const created = await chatApi.createConversation();
    const renamed = await chatApi.renameConversation(created.id, "   ");
    expect(renamed.title).toBe("گفتگوی جدید");
  });
});
