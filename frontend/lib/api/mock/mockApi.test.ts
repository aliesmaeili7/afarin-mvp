import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/types";
import { mockApi } from "./mockApi";
import { resetDb } from "./mockDb";
import { TOTAL_GENERATION_MS } from "./generation";
import type { EducationalAgentResult } from "@/types/domain";

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
  it("walks brief → signup → generation → finished campaign", async () => {
    const campaignId = await completeBrief();

    await mockApi.updateCampaign(campaignId, {
      requested_image_count: 1,
      selected_template_id: "hero_product",
    });

    await expect(mockApi.startGeneration(campaignId)).rejects.toBeInstanceOf(
      ApiError,
    );

    const session = await mockApi.signUpWithPassword({
      email: "shop@example.com",
      password: "shoppass1",
    });
    expect(session.user.email).toBe("shop@example.com");

    const started = await mockApi.startGeneration(campaignId);
    expect(started.status).toBe("queued");

    const inProgress = await mockApi.getCampaignStatus(campaignId);
    expect(inProgress.percent).toBeLessThan(100);
    expect(["queued", "generating"]).toContain(inProgress.status);

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
    expect(detail.visual_candidates).toHaveLength(1);

    expect(
      detail.copies.find((copy) => copy.copy_type === "caption_short")?.content,
    ).toContain("زعفران ممتاز");

    const feed = detail.assets.find((asset) => asset.asset_type === "feed_final");
    expect(feed?.metadata_json).toMatchObject({
      brand_name: "سحند",
      price_text: "۳۹۹ هزار تومان",
      product_image_path: "public://mock/product-saffron.svg",
    });
  }, 60_000);

  it("is idempotent when generation is triggered repeatedly", async () => {
    const campaignId = await completeBrief();
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
      product_image_path: "public://mock/product-saffron.svg",
    });
    expect(ready.thumbnail_spec?.headline_fa).toBeTruthy();
    // Still null in Phase 1: the browser composes the ad, so the card falls
    // back to the source photo only when there is no spec to render.
    expect(ready.thumbnail_path).toBe("public://mock/product-saffron.svg");
  }, 60_000);

  it("rejects a campaign belonging to somebody else", async () => {
    const campaignId = await completeBrief();
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

  it("persists a product crop without replacing the original upload", async () => {
    const campaign = await mockApi.createCampaign({});
    const images = await mockApi.useSampleProduct(campaign.id);
    const cropped = await mockApi.updateProductCrop(campaign.id, images[0].id, {
      x: 0.1,
      y: 0.2,
      width: 0.7,
      height: 0.6,
    });
    expect(cropped.storage_path).toBe(images[0].storage_path);
    expect(cropped.crop).toEqual({ x: 0.1, y: 0.2, width: 0.7, height: 0.6 });
    const detail = await mockApi.getCampaign(campaign.id);
    expect(detail.product_images[0].crop.height).toBe(0.6);
  });

  it("rewrites caption and headline through closed intents", async () => {
    const campaignId = await completeBrief();
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
    const started = await mockApi.startGeneration(second.id);
    expect(["queued", "generating"]).toContain(started.status);
  }, 60_000);

  it("never shows another campaign's package on a fresh draft", async () => {
    const firstId = await completeBrief();
    const second = await mockApi.createCampaign({});
    const detail = await mockApi.getCampaign(second.id);
    expect(detail.assets).toEqual([]);
    expect(detail.campaign.id).not.toBe(firstId);
  }, 60_000);

  it("keeps a brief complete after the product name changes", async () => {
    const campaignId = await completeBrief();
    await mockApi.saveProduct(campaignId, { name: "صابون زیتون" });
    const afterRename = await mockApi.getCampaign(campaignId);
    expect(afterRename.campaign.status).toBe("brief_complete");
    expect(afterRename.product?.name).toBe("صابون زیتون");
  }, 60_000);
});

describe("password recovery for OTP-only accounts", () => {
  it("does not tell an existing OTP user to sign up again", async () => {
    await mockApi.verifyEmailCode({ email: "otp@shop.com", code: "123456" });
    await mockApi.signOut();

    await expect(
      mockApi.signInWithPassword({ email: "otp@shop.com", password: "newpass1" }),
    ).rejects.toMatchObject({
      messageFa: "ایمیل یا رمز درست نیست.",
    });
  });

  it("lets an OTP-only account set a first password and then sign in", async () => {
    await mockApi.verifyEmailCode({ email: "otp@shop.com", code: "123456" });
    await mockApi.signOut();

    await mockApi.requestPasswordReset({ email: "otp@shop.com" });
    await mockApi.ensurePasswordRecoverySession();
    const afterReset = await mockApi.updatePassword({ password: "newpass12" });
    expect(afterReset.user.email).toBe("otp@shop.com");

    await mockApi.signOut();
    const signedIn = await mockApi.signInWithPassword({
      email: "otp@shop.com",
      password: "newpass12",
    });
    expect(signedIn.user.email).toBe("otp@shop.com");
  });

  it("rejects setting a password without a recovery session", async () => {
    await expect(mockApi.ensurePasswordRecoverySession()).rejects.toMatchObject({
      messageFa: "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
    });
    await expect(mockApi.updatePassword({ password: "newpass12" })).rejects.toMatchObject({
      messageFa: "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
    });
  });

  it("keeps OTP login working after a password is set", async () => {
    await mockApi.signUpWithPassword({
      email: "both@shop.com",
      password: "shoppass1",
    });
    await mockApi.signOut();
    const viaCode = await mockApi.verifyEmailCode({
      email: "both@shop.com",
      code: "654321",
    });
    expect(viaCode.user.email).toBe("both@shop.com");
  });
});

describe("mock educational journey", () => {
  it("rejects anonymous create and keeps themes listable", async () => {
    await expect(
      mockApi.createEducationalPost({ user_prompt: "یک پست درباره کسرها" }),
    ).rejects.toMatchObject({ code: "unauthorized" });

    const themes = await mockApi.listEducationalThemes();
    expect(themes.builtin.length).toBeGreaterThan(0);
    expect(themes.saved).toEqual([]);
  });

  it("creates one square post from a single prompt after signup", async () => {
    await mockApi.signUpWithPassword({
      email: "teacher@example.com",
      password: "teachpass1",
    });

    const created = await mockApi.createEducationalPost({
      user_prompt:
        "برای کلاس ششم یک پست درباره اعداد اعشاری مثل 0.5 و 1.25 بساز",
    });
    expect(created.status).toBe("queued");
    expect(created.selected_theme_id).toBeNull();

    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + 20_000);

    const status = await mockApi.getEducationalPostStatus(created.id);
    expect(status.status).toBe("ready");
    expect(status.percent).toBe(100);

    const post = await mockApi.getEducationalPost(created.id);
    expect(post.language).toBe("fa");
    expect(post.render_spec_json.render_mode).toBe("educational");
    expect(
      "image_path" in post.render_spec_json && post.render_spec_json.image_path,
    ).toBeTruthy();
    expect(post.render_spec_json).not.toHaveProperty("text_layers");
    expect(post.render_spec_json).not.toHaveProperty("cta_fa");
    expect(post.render_spec_json).not.toHaveProperty("headline_fa");
    expect(post.render_spec_json).not.toHaveProperty("template_id");
    const agent = post.agent_json as EducationalAgentResult;
    expect(agent.final_prompt).toContain("0.5");
    expect(agent.final_prompt).toContain("1.25");
    expect(agent).not.toHaveProperty("content");
    expect(post.theme_json).not.toHaveProperty("typography");
  });

  it("saves a generated theme without the lesson itself", async () => {
    await mockApi.signUpWithPassword({
      email: "theme@example.com",
      password: "themepass1",
    });
    const created = await mockApi.createEducationalPost({
      user_prompt: "یک پست درباره کسرهای مساوی",
    });
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(Date.now() + 20_000);
    await mockApi.getEducationalPostStatus(created.id);

    const saved = await mockApi.saveEducationalTheme({ post_id: created.id });
    expect(saved.source).toBe("user");
    expect(JSON.stringify(saved.theme_json)).not.toContain(created.user_prompt);
    expect(saved.theme_json).not.toHaveProperty("final_prompt");
    expect(saved.theme_json).not.toHaveProperty("educational_concept");

    const listed = await mockApi.listEducationalThemes();
    expect(listed.saved.map((theme) => theme.id)).toContain(saved.id);

    const reused = await mockApi.createEducationalPost({
      user_prompt: "یک پست درباره ضرب",
      theme_id: saved.id,
    });
    expect(reused.selected_theme_id).toBe(saved.id);
  });
});

