import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase/client", () => ({
  getSupabaseClient: () => ({
    auth: { getSession: async () => ({ data: { session: null } }) },
  }),
  getAccessToken: async () => "token",
}));

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function loadApi() {
  return (await import("./httpChatApi")).httpChatApi;
}

const summary = {
  id: "c1",
  title: "سلام",
  language: "fa",
  active_theme: {
    id: "saved-clay",
    source: "chat_catalog",
    name: "خمیری و بازیگوش",
    style_json: {},
  },
  pinned: false,
  archived: false,
  pinned_at: null,
  created_at: "2026-09-01T00:00:00.000Z",
  updated_at: "2026-09-01T00:00:00.000Z",
};

const conversation = {
  ...summary,
  messages: [
    {
      id: "m1",
      conversation_id: "c1",
      role: "user",
      content: "سلام",
      language: "fa",
      metadata_json: {},
      created_at: "2026-09-01T00:00:00.000Z",
    },
  ],
  artifacts: [],
  has_older_messages: false,
};

describe("http ChatApi", () => {
  it("creates a conversation by sending the first message", async () => {
    const api = await loadApi();
    fetchMock.mockResolvedValueOnce(jsonResponse(conversation));

    const result = await api.sendMessage(null, {
      content: "سلام",
      language: "fa",
      activeTheme: summary.active_theme,
    });

    expect(result.conversation.id).toBe("c1");
    const [path, init] = fetchMock.mock.calls[0];
    expect(String(path)).toContain("/api/chat/conversations");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toMatchObject({
      content: "سلام",
      language: "fa",
    });
  });

  it("lists, searches, and loads archived conversations", async () => {
    const api = await loadApi();
    fetchMock
      .mockResolvedValueOnce(jsonResponse([summary]))
      .mockResolvedValueOnce(jsonResponse([summary]))
      .mockResolvedValueOnce(jsonResponse([]));

    await api.listConversations();
    await api.searchConversations("کفش");
    await api.listArchivedConversations();

    expect(String(fetchMock.mock.calls[1][0])).toContain("q=%DA%A9%D9%81%D8%B4");
    expect(String(fetchMock.mock.calls[2][0])).toContain("archived=true");
  });

  it("patches rename, pin, archive, restore, and theme", async () => {
    const api = await loadApi();
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse(conversation)));

    await api.renameConversation("c1", "کفش");
    await api.pinConversation("c1");
    await api.unpinConversation("c1");
    await api.archiveConversation("c1");
    await api.restoreConversation("c1");
    await api.setActiveTheme("c1", "saved-clay");
    await api.setActiveTheme("c1", null);

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({
      title: "کفش",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[1][1].body))).toEqual({
      pinned: true,
    });
    expect(
      JSON.parse(String(fetchMock.mock.calls[5][1].body)).active_theme.id,
    ).toBe("saved-clay");
    expect(
      JSON.parse(String(fetchMock.mock.calls[5][1].body)).active_theme.swatch,
    ).toBeUndefined();
    expect(JSON.parse(String(fetchMock.mock.calls[6][1].body))).toEqual({
      active_theme: null,
    });
  });

  it("deletes a conversation", async () => {
    const api = await loadApi();
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await api.deleteConversation("c1");
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });

  it("resolves artifact urls after fetch", async () => {
    const api = await loadApi();
    const withArt = {
      ...conversation,
      artifacts: [
        {
          id: "a1",
          conversation_id: "c1",
          message_id: "m1",
          artifact_type: "image",
          storage_path: "supabase://product-images/chat/c1/artifacts/x.png",
          aspect_ratio: "1:1",
          status: "ready",
          metadata_json: {},
          created_at: "2026-09-01T00:00:00.000Z",
        },
      ],
    };
    fetchMock
      .mockResolvedValueOnce(jsonResponse(withArt))
      .mockResolvedValueOnce(
        jsonResponse({
          "supabase://product-images/chat/c1/artifacts/x.png":
            "https://signed/x.png",
        }),
      );

    const loaded = await api.getConversation("c1");
    expect(loaded.artifacts[0]?.url).toBe("https://signed/x.png");
  });
});
