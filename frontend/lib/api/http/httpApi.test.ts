import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getSession = vi.fn(async () => ({ data: { session: null } }));

vi.mock("@/lib/supabase/client", () => ({
  getSupabaseClient: () => ({ auth: { getSession } }),
  getAccessToken: async () => null,
}));

const fetchMock = vi.fn();

beforeEach(async () => {
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
  return (await import("./httpApi")).httpApi;
}

describe("request handling", () => {
  it("sends the anonymous session cookie on every call", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(jsonResponse({ id: "c1" }));

    await httpApi.createCampaign({});

    const [, init] = fetchMock.mock.calls[0];
    // The cookie is HttpOnly, so this flag is the only way it travels.
    expect(init.credentials).toBe("include");
  });

  it("surfaces the backend's Persian message rather than a status code", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(
      jsonResponse(
        { code: "unauthorized", message_fa: "دسترسی به این کمپین برای شما مجاز نیست." },
        403,
      ),
    );

    await expect(httpApi.getCampaign("c1")).rejects.toMatchObject({
      code: "unauthorized",
      messageFa: "دسترسی به این کمپین برای شما مجاز نیست.",
    });
  });

  it("falls back to a Persian message when the server replies with HTML", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(
      new Response("<html>502 Bad Gateway</html>", { status: 502 }),
    );

    await expect(httpApi.listCampaigns()).rejects.toMatchObject({
      code: "unknown",
      messageFa: "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.",
    });
  });

  it("explains a dead connection in Persian", async () => {
    const httpApi = await loadApi();
    // resetModules gives each test a fresh graph, so ApiError must come from
    // the same one the client threw from for instanceof to hold.
    const { ApiError } = await import("../types");
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const error = await httpApi.listCampaigns().catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.messageFa).toBe("ارتباط با سرور برقرار نشد. اینترنتت رو چک کن.");
    // The original failure stays attached for debugging, never shown to users.
    expect(error.cause).toBeInstanceOf(TypeError);
  });

  it("treats 204 as success with no body", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(httpApi.deleteProductImage("c1", "i1")).resolves.toBeUndefined();
  });
});

describe("asset resolution", () => {
  it("resolves bundled assets without contacting the server", async () => {
    const httpApi = await loadApi();

    const url = await httpApi.resolveAssetUrl("public://mock/product-saffron.svg");

    expect(url).toBe("/mock/product-saffron.svg");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("batches concurrent lookups into a single request", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(
      jsonResponse({
        "supabase://product-images/a": "https://signed/a",
        "supabase://product-images/b": "https://signed/b",
      }),
    );

    const [first, second] = await Promise.all([
      httpApi.resolveAssetUrl("supabase://product-images/a"),
      httpApi.resolveAssetUrl("supabase://product-images/b"),
    ]);

    expect(first).toBe("https://signed/a");
    expect(second).toBe("https://signed/b");
    // Five ad canvases mounting at once must not mean five round trips.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).paths).toEqual([
      "supabase://product-images/a",
      "supabase://product-images/b",
    ]);
  });

  it("returns null for an asset the server refuses to sign", async () => {
    const httpApi = await loadApi();
    fetchMock.mockResolvedValue(jsonResponse({ "supabase://x/y": null }));

    await expect(httpApi.resolveAssetUrl("supabase://x/y")).resolves.toBeNull();
  });
});

describe("email sign-in", () => {
  it("rejects a malformed address before sending anything", async () => {
    const httpApi = await loadApi();

    await expect(
      httpApi.requestEmailCode({ email: "not-an-email" }),
    ).rejects.toMatchObject({ messageFa: "ایمیل معتبر وارد کن." });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects an incomplete code before calling the provider", async () => {
    const httpApi = await loadApi();

    await expect(
      httpApi.verifyEmailCode({ email: "a@b.com", code: "123" }),
    ).rejects.toMatchObject({ messageFa: "کد ۶ رقمی رو کامل وارد کن." });
  });
});
