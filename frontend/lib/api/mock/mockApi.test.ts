import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/types";
import { mockApi } from "./mockApi";
import { resetDb } from "./mockDb";
import { TOTAL_GENERATION_MS } from "./generation";

/**
 * End-to-end exercise of the mocked backend along the real user journey, so
 * regressions in the state machine surface without a browser.
 */
async function completeBrief() {
  const campaign = await mockApi.createCampaign({});
  expect(campaign.status).toBe("draft");

  const images = await mockApi.useSampleProduct(campaign.id);
  expect(images).toHaveLength(1);

  await mockApi.saveProduct(campaign.id, {
    name: "زعفران ممتاز",
    description: "زعفران یک گرمی مناسب هدیه",
    price_text: "۳۹۹ هزار تومان",
    main_benefit: "بسته‌بندی هدیه و کیفیت صادراتی",
    brand_name: "سحند",
  });

  await mockApi.updateCampaign(campaign.id, {
    objective: "sell_product",
    audience: "کسانی که دنبال هدیه لوکس هستن",
  });
  const withStyle = await mockApi.updateCampaign(campaign.id, {
    visual_style: "luxury",
  });
  expect(withStyle.status).toBe("brief_complete");

  return campaign.id;
}

beforeEach(() => {
  resetDb();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("mock campaign journey", () => {
  it("walks brief → concepts → signup → generation → finished campaign", async () => {
    const campaignId = await completeBrief();

    const concepts = await mockApi.generateConcepts(campaignId);
    expect(concepts).toHaveLength(3);
    expect(new Set(concepts.map((c) => c.title_fa)).size).toBe(3);
    expect(concepts[0].headline_fa).toContain("زعفران ممتاز");

    const secondRound = await mockApi.generateConcepts(campaignId);
    expect(secondRound.map((c) => c.title_fa)).not.toEqual(
      concepts.map((c) => c.title_fa),
    );

    const selected = await mockApi.selectConcept(campaignId, secondRound[0].id);
    expect(selected.status).toBe("concept_selected");

    // The signup gate is enforced by the API, not only by the UI.
    await expect(mockApi.startGeneration(campaignId)).rejects.toBeInstanceOf(
      ApiError,
    );

    const session = await mockApi.verifyEmailCode({ email: "shop@example.com", code: "123456" });
    expect(session.user.email).toBe("shop@example.com");

    const started = await mockApi.startGeneration(campaignId);
    expect(started.status).toBe("queued");

    const inProgress = await mockApi.getCampaignStatus(campaignId);
    expect(inProgress.percent).toBeLessThan(100);
    expect(["queued", "generating"]).toContain(inProgress.status);

    // Only Date is faked so the API's own setTimeout delays still resolve.
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + TOTAL_GENERATION_MS + 5000);

    const finished = await mockApi.getCampaignStatus(campaignId);
    expect(finished.status).toBe("ready");
    expect(finished.percent).toBe(100);

    const detail = await mockApi.getCampaign(campaignId);
    expect(detail.campaign.status).toBe("ready");

    const assetTypes = detail.assets.map((asset) => asset.asset_type).sort();
    expect(assetTypes).toEqual([
      "carousel_1",
      "carousel_2",
      "carousel_3",
      "feed_final",
      "story_final",
    ]);

    const copyTypes = detail.copies.map((copy) => copy.copy_type);
    expect(copyTypes).toContain("caption_short");
    expect(copyTypes).toContain("caption_friendly");
    expect(copyTypes).toContain("caption_persuasive");
    expect(copyTypes).toContain("cta");
    expect(copyTypes).toContain("hashtags");
    expect(copyTypes).toContain("reel_concept");
    expect(copyTypes.filter((type) => type === "story")).toHaveLength(3);

    expect(
      detail.copies.find((copy) => copy.copy_type === "caption_short")?.content,
    ).toContain("زعفران ممتاز");

    // The brief flows into the composed asset rather than being thrown away.
    const feed = detail.assets.find((asset) => asset.asset_type === "feed_final");
    expect(feed?.metadata_json).toMatchObject({
      brand_name: "سحند",
      price_text: "۳۹۹ هزار تومان",
      product_image_path: "public://mock/product-saffron.svg",
    });
  }, 60_000);

  it("is idempotent when generation is triggered repeatedly", async () => {
    const campaignId = await completeBrief();
    const concepts = await mockApi.generateConcepts(campaignId);
    await mockApi.selectConcept(campaignId, concepts[0].id);
    await mockApi.verifyEmailCode({ email: "repeat@example.com", code: "123456" });

    const first = await mockApi.startGeneration(campaignId);
    const second = await mockApi.startGeneration(campaignId);
    const third = await mockApi.startGeneration(campaignId);

    expect(first.campaign_id).toBe(campaignId);
    expect(["queued", "generating"]).toContain(second.status);
    expect(["queued", "generating"]).toContain(third.status);

    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + TOTAL_GENERATION_MS + 5000);

    const finished = await mockApi.getCampaignStatus(campaignId);
    expect(finished.status).toBe("ready");

    const detail = await mockApi.getCampaign(campaignId);
    // A second job would have produced a duplicate set of assets.
    expect(detail.assets).toHaveLength(5);
  }, 60_000);

  it("summarises a finished campaign with its feed ad, not the raw photo", async () => {
    const campaignId = await completeBrief();
    const concepts = await mockApi.generateConcepts(campaignId);
    await mockApi.selectConcept(campaignId, concepts[0].id);
    await mockApi.verifyEmailCode({ email: "thumb@example.com", code: "123456" });

    const [beforeGeneration] = await mockApi.listCampaigns();
    expect(beforeGeneration.thumbnail_spec).toBeNull();
    expect(beforeGeneration.thumbnail_path).toBe(
      "public://mock/product-saffron.svg",
    );

    await mockApi.startGeneration(campaignId);
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + TOTAL_GENERATION_MS + 5000);
    await mockApi.getCampaignStatus(campaignId);

    const [ready] = await mockApi.listCampaigns();
    expect(ready.thumbnail_spec).toMatchObject({
      headline_fa: concepts[0].headline_fa,
      product_image_path: "public://mock/product-saffron.svg",
    });
    // Still null in Phase 1: the browser composes the ad, so the card falls
    // back to the source photo only when there is no spec to render.
    expect(ready.thumbnail_path).toBe("public://mock/product-saffron.svg");
  }, 60_000);

  it("rejects a campaign belonging to somebody else", async () => {
    const campaignId = await completeBrief();
    const concepts = await mockApi.generateConcepts(campaignId);
    await mockApi.selectConcept(campaignId, concepts[0].id);
    await mockApi.verifyEmailCode({ email: "owner@example.com", code: "123456" });
    await mockApi.signOut();
    await mockApi.verifyEmailCode({ email: "stranger@example.com", code: "123456" });

    await expect(mockApi.getCampaign(campaignId)).rejects.toMatchObject({
      code: "unauthorized",
    });
  }, 60_000);

  it("maps storage paths to displayable URLs", async () => {
    expect(await mockApi.resolveAssetUrl("public://mock/product-saffron.svg")).toBe(
      "/mock/product-saffron.svg",
    );
    expect(await mockApi.resolveAssetUrl(null)).toBeNull();
  });

  it("rewrites caption and headline through closed intents", async () => {
    const campaignId = await completeBrief();
    const concepts = await mockApi.generateConcepts(campaignId);
    await mockApi.selectConcept(campaignId, concepts[0].id);
    await mockApi.verifyEmailCode({ email: "rewrite@example.com", code: "123456" });
    await mockApi.startGeneration(campaignId);

    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + TOTAL_GENERATION_MS + 5000);
    await mockApi.getCampaignStatus(campaignId);

    const detail = await mockApi.getCampaign(campaignId);
    const caption = detail.copies.find((copy) => copy.copy_type === "caption_short");
    expect(caption).toBeDefined();
    const rewritten = await mockApi.rewriteCopy(campaignId, caption!.id, "informal");
    expect(rewritten.content).toContain("😊");

    const feed = detail.assets.find((asset) => asset.asset_type === "feed_final");
    expect(feed).toBeDefined();
    const asset = await mockApi.rewriteAssetText(
      campaignId,
      feed!.id,
      "new_headline",
    );
    expect(
      (asset.metadata_json as { headline_fa: string }).headline_fa,
    ).toContain("انتخاب هوشمندانه‌تر");
  }, 60_000);

  it("lets a signed-in user generate a second campaign without signing up again", async () => {
    const firstId = await completeBrief();
    const firstConcepts = await mockApi.generateConcepts(firstId);
    await mockApi.selectConcept(firstId, firstConcepts[0].id);
    await expect(mockApi.startGeneration(firstId)).rejects.toBeInstanceOf(ApiError);

    await mockApi.verifyEmailCode({ email: "repeat@shop.com", code: "123456" });
    await mockApi.startGeneration(firstId);
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + TOTAL_GENERATION_MS + 5000);
    await mockApi.getCampaignStatus(firstId);

    const second = await mockApi.createCampaign({});
    await mockApi.saveProduct(second.id, { name: "صابون زیتون", brand_name: "زیتونک" });
    await mockApi.updateCampaign(second.id, {
      objective: "sell_product",
      visual_style: "minimal",
    });
    const secondConcepts = await mockApi.generateConcepts(second.id);
    expect(secondConcepts).toHaveLength(3);
    const first = await mockApi.getCampaign(firstId);
    expect(secondConcepts.map((item) => item.id)).not.toEqual(
      first.concepts.map((item) => item.id),
    );
    await mockApi.selectConcept(second.id, secondConcepts[0].id);
    const started = await mockApi.startGeneration(second.id);
    expect(["queued", "generating"]).toContain(started.status);
  }, 60_000);

  it("never shows another campaign's concepts on a fresh draft", async () => {
    const firstId = await completeBrief();
    const firstConcepts = await mockApi.generateConcepts(firstId);
    expect(firstConcepts[0].headline_fa).toContain("زعفران");

    const second = await mockApi.createCampaign({});
    const detail = await mockApi.getCampaign(second.id);
    expect(detail.concepts).toEqual([]);
    expect(detail.campaign.id).not.toBe(firstId);
  }, 60_000);

  it("invalidates concepts when the brief changes", async () => {
    const campaignId = await completeBrief();
    const generated = await mockApi.generateConcepts(campaignId);
    await mockApi.selectConcept(campaignId, generated[0].id);

    const patched = await mockApi.updateCampaign(campaignId, {
      visual_style: "minimal",
    });
    expect(patched.status).toBe("brief_complete");
    expect(patched.selected_concept_id).toBeNull();
    expect((await mockApi.getCampaign(campaignId)).concepts).toEqual([]);

    const regenerated = await mockApi.generateConcepts(campaignId);
    expect(regenerated).toHaveLength(3);
    await mockApi.updateCampaign(campaignId, { visual_style: "minimal" });
    expect((await mockApi.getCampaign(campaignId)).concepts).toHaveLength(3);

    await mockApi.saveProduct(campaignId, { name: "صابون زیتون" });
    const afterRename = await mockApi.getCampaign(campaignId);
    expect(afterRename.concepts).toEqual([]);
    expect(afterRename.campaign.status).toBe("brief_complete");
  }, 60_000);
});
