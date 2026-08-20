import type {
  AssetRenderSpec,
  Brand,
  Campaign,
  CampaignAsset,
  CampaignConcept,
  CampaignCopy,
  CampaignDetail,
  CampaignStatus,
  CampaignStatusResponse,
  CampaignSummary,
  CopyType,
  Product,
  ProductImage,
  Session,
} from "@/types/domain";
import {
  ApiError,
  type AfarinApi,
  type AssetTextPatch,
  type BrandInput,
  type CreateCampaignInput,
  type ProductInput,
  type EmailCodeRequest,
  type EmailCodeVerification,
  type RewriteIntent,
  type UpdateCampaignInput,
} from "@/lib/api/types";
import { backgroundsForStyle } from "@/lib/content/backgrounds";
import * as imageStore from "@/lib/storage/imageStore";
import {
  buildConcepts,
  buildSubheadline,
  type ConceptFixture,
} from "./fixtures/concepts";
import {
  buildCaptions,
  buildHashtags,
  buildPrimaryCta,
  buildReelConcept,
  buildStoryIdeas,
} from "./fixtures/copy";
import type { CopyContext } from "./fixtures/context";
import { computeGenerationProgress } from "./generation";
import { delay, getFailureMode, LATENCY } from "./latency";
import {
  mutateDb,
  newId,
  nowIso,
  readDb,
  SAMPLE_BRAND_ID,
  SAMPLE_CAMPAIGN_ID,
  SAMPLE_IMAGE_PATH,
  writeDb,
  type MockDbShape,
} from "./mockDb";

const QUEUE_DURATION_MS = 900;

function findCampaign(db: MockDbShape, campaignId: string): Campaign {
  const campaign = db.campaigns.find((item) => item.id === campaignId);
  if (!campaign) {
    throw new ApiError("not_found", "این کمپین پیدا نشد.");
  }
  return campaign;
}

/** Mirrors the ownership rule of spec §27: IDs alone must not grant access. */
function assertOwnership(db: MockDbShape, campaign: Campaign): void {
  if (campaign.user_id) {
    if (!db.session || db.session.user.id !== campaign.user_id) {
      throw new ApiError("unauthorized", "دسترسی به این کمپین برای شما مجاز نیست.");
    }
    return;
  }
  if (
    campaign.anonymous_session_id &&
    campaign.anonymous_session_id !== db.anonymous_session_id
  ) {
    throw new ApiError("unauthorized", "دسترسی به این کمپین برای شما مجاز نیست.");
  }
}

function productOf(db: MockDbShape, campaign: Campaign): Product | null {
  if (!campaign.product_id) return null;
  return db.products.find((item) => item.id === campaign.product_id) ?? null;
}

function primaryImagePath(db: MockDbShape, campaign: Campaign): string | null {
  if (!campaign.product_id) return null;
  const images = db.product_images.filter(
    (image) => image.product_id === campaign.product_id,
  );
  const primary = images.find((image) => image.is_primary) ?? images[0];
  return primary?.storage_path ?? null;
}

function brandOf(db: MockDbShape, campaign: Campaign): Brand | null {
  if (!campaign.brand_id) return null;
  return db.brands.find((item) => item.id === campaign.brand_id) ?? null;
}

function buildCopyContext(db: MockDbShape, campaign: Campaign): CopyContext {
  const product = productOf(db, campaign);
  const brand = brandOf(db, campaign);
  return {
    productName: product?.name?.trim() || "محصول شما",
    description: product?.description ?? null,
    priceText: product?.price_text ?? null,
    benefit: product?.main_benefit ?? null,
    brandName: brand?.name ?? null,
    audience: campaign.audience,
    objective: campaign.objective ?? "sell_product",
    style: campaign.visual_style ?? "modern",
    round: db.concept_rounds[campaign.id] ?? 0,
  };
}

function ensureProduct(db: MockDbShape, campaign: Campaign): Product {
  const existing = productOf(db, campaign);
  if (existing) return existing;

  const product: Product = {
    id: newId("prd"),
    user_id: db.session?.user.id ?? null,
    brand_id: campaign.brand_id,
    name: "",
    description: null,
    price_text: null,
    main_benefit: null,
    created_at: nowIso(),
    updated_at: nowIso(),
  };
  db.products.push(product);
  campaign.product_id = product.id;
  return product;
}

function conceptsOf(db: MockDbShape, campaignId: string): CampaignConcept[] {
  return db.campaign_concepts
    .filter((concept) => concept.campaign_id === campaignId)
    .sort((a, b) => a.concept_number - b.concept_number);
}

function dropStaleConcepts(
  db: MockDbShape,
  campaign: Campaign,
  changed: boolean,
): void {
  if (!changed) return;
  if (campaign.status !== "concepts_ready" && campaign.status !== "concept_selected") {
    return;
  }
  db.campaign_concepts = db.campaign_concepts.filter(
    (concept) => concept.campaign_id !== campaign.id,
  );
  campaign.selected_concept_id = null;
  delete db.concept_rounds[campaign.id];
  if (campaign.product_id && campaign.objective && campaign.visual_style) {
    campaign.status = "brief_complete";
  } else {
    campaign.status = "draft";
  }
}

function blank(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function writeConcepts(
  db: MockDbShape,
  campaign: Campaign,
  fixtures: ConceptFixture[],
): CampaignConcept[] {
  db.campaign_concepts = db.campaign_concepts.filter(
    (concept) => concept.campaign_id !== campaign.id,
  );

  const created = fixtures.map((fixture, index) => {
    const concept: CampaignConcept = {
      id: newId("cnc"),
      campaign_id: campaign.id,
      concept_number: index + 1,
      title_fa: fixture.title_fa,
      headline_fa: fixture.headline_fa,
      description_fa: fixture.description_fa,
      visual_direction: fixture.visual_direction,
      background_prompt: fixture.background_prompt,
      raw_json: { background_id: fixture.background_id },
      selected: false,
      created_at: nowIso(),
    };
    return concept;
  });

  db.campaign_concepts.push(...created);
  return created;
}

function conceptBackgroundId(concept: CampaignConcept, campaign: Campaign): string {
  const fromRaw = concept.raw_json?.background_id;
  if (typeof fromRaw === "string") return fromRaw;
  return backgroundsForStyle(campaign.visual_style ?? "modern")[0].id;
}

function upsertCopy(
  db: MockDbShape,
  campaignId: string,
  copyType: CopyType,
  content: string,
  metadata: Record<string, unknown> = {},
): void {
  db.campaign_copy.push({
    id: newId("cpy"),
    campaign_id: campaignId,
    copy_type: copyType,
    content,
    metadata_json: metadata,
    created_at: nowIso(),
    updated_at: nowIso(),
  });
}

function buildAssetSpec(
  base: Omit<AssetRenderSpec, "slide_label_fa">,
  overrides: Partial<AssetRenderSpec> = {},
): AssetRenderSpec {
  return { ...base, slide_label_fa: null, ...overrides };
}

/**
 * Produces the campaign output rows.
 *
 * Called both when a mocked generation finishes and lazily for the seeded
 * sample campaign, so there is exactly one definition of "what a finished
 * campaign contains".
 */
function materializeCampaign(
  db: MockDbShape,
  campaign: Campaign,
): CampaignStatus {
  const ctx = buildCopyContext(db, campaign);

  let concepts = conceptsOf(db, campaign.id);
  if (concepts.length === 0) {
    concepts = writeConcepts(db, campaign, buildConcepts(ctx));
  }

  let selected = concepts.find((concept) => concept.selected);
  if (!selected) {
    selected = concepts[0];
    selected.selected = true;
    campaign.selected_concept_id = selected.id;
  }

  db.campaign_copy = db.campaign_copy.filter(
    (copy) => copy.campaign_id !== campaign.id,
  );

  const captions = buildCaptions(ctx);
  upsertCopy(db, campaign.id, "caption_short", captions.caption_short);
  upsertCopy(db, campaign.id, "caption_friendly", captions.caption_friendly);
  upsertCopy(db, campaign.id, "caption_persuasive", captions.caption_persuasive);

  buildStoryIdeas(ctx).forEach((story, index) => {
    upsertCopy(db, campaign.id, "story", story, { order: index });
  });

  upsertCopy(db, campaign.id, "cta", buildPrimaryCta(ctx));
  upsertCopy(db, campaign.id, "hashtags", buildHashtags(ctx));

  const reel = buildReelConcept(ctx);
  upsertCopy(db, campaign.id, "reel_concept", reel.hook_fa, {
    reel: reel as unknown as Record<string, unknown>,
  });

  const backgroundId = conceptBackgroundId(selected, campaign);
  const brand = brandOf(db, campaign);
  const base: Omit<AssetRenderSpec, "slide_label_fa"> = {
    template_id: "feed_classic",
    background_id: backgroundId,
    headline_fa: selected.headline_fa,
    subheadline_fa: buildSubheadline(ctx),
    cta_fa: buildPrimaryCta(ctx),
    price_text: ctx.priceText,
    brand_name: brand?.name ?? ctx.brandName,
    product_image_path: primaryImagePath(db, campaign),
  };

  const failureMode = getFailureMode();

  db.campaign_assets = db.campaign_assets.filter(
    (asset) => asset.campaign_id !== campaign.id,
  );

  const push = (
    assetType: CampaignAsset["asset_type"],
    width: number,
    height: number,
    spec: AssetRenderSpec,
  ) => {
    db.campaign_assets.push({
      id: newId("ast"),
      campaign_id: campaign.id,
      asset_type: assetType,
      // Phase 1 composes in the browser; Phase 4/5 will fill this in.
      storage_path: null,
      width,
      height,
      template_id: spec.template_id,
      metadata_json: spec,
      created_at: nowIso(),
    });
  };

  push("feed_final", 1080, 1350, buildAssetSpec(base));

  // A partial failure keeps the row so the user can retry just that asset.
  push(
    "story_final",
    1080,
    1920,
    buildAssetSpec(base, {
      template_id: "story_classic",
      failed: failureMode === "partial",
    }),
  );

  push(
    "carousel_1",
    1080,
    1350,
    buildAssetSpec(base, {
      template_id: "carousel_hook",
      slide_label_fa: "۱",
    }),
  );
  push(
    "carousel_2",
    1080,
    1350,
    buildAssetSpec(base, {
      template_id: "carousel_benefit",
      headline_fa: ctx.benefit ?? ctx.description ?? "چرا این محصول؟",
      subheadline_fa: ctx.productName,
      slide_label_fa: "۲",
    }),
  );
  push(
    "carousel_3",
    1080,
    1350,
    buildAssetSpec(base, {
      template_id: "carousel_cta",
      headline_fa: buildPrimaryCta(ctx),
      subheadline_fa: ctx.priceText ?? ctx.productName,
      slide_label_fa: "۳",
    }),
  );

  campaign.status = failureMode === "partial" ? "partial_failed" : "ready";
  campaign.updated_at = nowIso();
  return campaign.status;
}

function isEmail(value: string): boolean {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim().toLowerCase());
}

/**
 * Creates or reuses a local profile and transfers the anonymous campaign to it,
 * standing in for what Supabase Auth plus POST /api/session/adopt do for real.
 */
function createMockSession(rawEmail: string): Session {
  const email = rawEmail.trim().toLowerCase();

  return mutateDb((db) => {
    const existing = db.profiles.find((profile) => profile.email === email);
    const profile = existing ?? {
      id: newId("usr"),
      user_id: newId("usr"),
      display_name: email.split("@")[0],
      email,
      locale: "fa",
      credit_balance_cached: 0,
      free_campaigns_remaining: 1,
      created_at: nowIso(),
      updated_at: nowIso(),
    };
    if (!existing) db.profiles.push(profile);

    const session: Session = {
      user: {
        id: profile.id,
        email: profile.email,
        display_name: profile.display_name,
        locale: profile.locale,
        free_campaigns_remaining: profile.free_campaigns_remaining,
      },
      access_token: newId("mocktoken"),
    };
    db.session = session;

    // The anonymous campaign becomes owned by the new account (spec §11).
    db.campaigns.forEach((campaign) => {
      if (campaign.anonymous_session_id === db.anonymous_session_id) {
        campaign.user_id = profile.id;
        campaign.anonymous_session_id = null;
        const product = productOf(db, campaign);
        if (product) product.user_id = profile.id;
        const brand = brandOf(db, campaign);
        if (brand && !brand.user_id) brand.user_id = profile.id;
      }
    });

    // Hand the seeded sample to the first account so the dashboard has
    // something to explore immediately.
    if (db.sample_unclaimed) {
      db.sample_unclaimed = false;
      const sample = db.campaigns.find((item) => item.id === SAMPLE_CAMPAIGN_ID);
      if (sample) {
        sample.user_id = profile.id;
        const product = productOf(db, sample);
        if (product) product.user_id = profile.id;
      }
      const sampleBrand = db.brands.find((item) => item.id === SAMPLE_BRAND_ID);
      if (sampleBrand) sampleBrand.user_id = profile.id;
    }

    return session;
  });
}

function ensureMaterialized(db: MockDbShape, campaign: Campaign): void {
  const hasAssets = db.campaign_assets.some(
    (asset) => asset.campaign_id === campaign.id,
  );
  if (!hasAssets && (campaign.status === "ready" || campaign.status === "partial_failed")) {
    materializeCampaign(db, campaign);
  }
}

/**
 * A finished campaign is represented by its feed ad, not by the photo the user
 * uploaded, so the dashboard shows what they actually made.
 */
function thumbnailOf(
  db: MockDbShape,
  campaign: Campaign,
): Pick<CampaignSummary, "thumbnail_path" | "thumbnail_spec"> {
  const feed = db.campaign_assets.find(
    (asset) => asset.campaign_id === campaign.id && asset.asset_type === "feed_final",
  );
  const spec = feed?.metadata_json as AssetRenderSpec | undefined;

  return {
    thumbnail_path: feed?.storage_path ?? primaryImagePath(db, campaign),
    thumbnail_spec: spec?.headline_fa ? spec : null,
  };
}

function summarize(db: MockDbShape, campaign: Campaign): CampaignSummary {
  const product = productOf(db, campaign);
  const brand = brandOf(db, campaign);
  return {
    id: campaign.id,
    product_name: product?.name?.trim() || null,
    brand_name: brand?.name ?? null,
    status: campaign.status,
    ...thumbnailOf(db, campaign),
    created_at: campaign.created_at,
  };
}

function statusResponse(
  campaign: Campaign,
  stage: CampaignStatusResponse["stage"],
  percent: number,
  messageFa: string | null,
  failedAssetTypes: CampaignStatusResponse["failed_asset_types"] = [],
): CampaignStatusResponse {
  return {
    campaign_id: campaign.id,
    status: campaign.status,
    stage,
    percent,
    message_fa: messageFa,
    failed_asset_types: failedAssetTypes,
  };
}

export const mockApi: AfarinApi = {
  async createCampaign(input: CreateCampaignInput): Promise<Campaign> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign: Campaign = {
        id: newId("cmp"),
        user_id: db.session?.user.id ?? null,
        anonymous_session_id: db.session ? null : db.anonymous_session_id,
        brand_id: input.brand_id ?? null,
        product_id: null,
        objective: null,
        audience: null,
        visual_style: null,
        selected_concept_id: null,
        status: "draft",
        is_free_campaign: true,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      db.campaigns.push(campaign);
      return campaign;
    });
  },

  async getCampaign(campaignId: string): Promise<CampaignDetail> {
    await delay(LATENCY.read);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      ensureMaterialized(db, campaign);

      return {
        campaign: { ...campaign },
        product: productOf(db, campaign),
        product_images: campaign.product_id
          ? db.product_images.filter(
              (image) => image.product_id === campaign.product_id,
            )
          : [],
        concepts: conceptsOf(db, campaign.id),
        copies: db.campaign_copy.filter((copy) => copy.campaign_id === campaign.id),
        assets: db.campaign_assets.filter(
          (asset) => asset.campaign_id === campaign.id,
        ),
        brand: brandOf(db, campaign),
      };
    });
  },

  async updateCampaign(
    campaignId: string,
    patch: UpdateCampaignInput,
  ): Promise<Campaign> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const changed =
        (patch.objective !== undefined &&
          blank(patch.objective) !== blank(campaign.objective)) ||
        (patch.audience !== undefined &&
          blank(patch.audience) !== blank(campaign.audience)) ||
        (patch.visual_style !== undefined &&
          blank(patch.visual_style) !== blank(campaign.visual_style)) ||
        (patch.brand_id !== undefined && patch.brand_id !== campaign.brand_id);

      if (patch.objective !== undefined) campaign.objective = patch.objective;
      if (patch.audience !== undefined) campaign.audience = patch.audience;
      if (patch.visual_style !== undefined) {
        campaign.visual_style = patch.visual_style;
      }
      if (patch.brand_id !== undefined) campaign.brand_id = patch.brand_id;

      dropStaleConcepts(db, campaign, changed);

      if (
        campaign.status === "draft" &&
        campaign.product_id &&
        campaign.objective &&
        campaign.visual_style
      ) {
        campaign.status = "brief_complete";
      }
      campaign.updated_at = nowIso();
      return { ...campaign };
    });
  },

  async listCampaigns(): Promise<CampaignSummary[]> {
    await delay(LATENCY.read);
    return mutateDb((db) => {
      const owned = db.campaigns.filter((campaign) =>
        db.session
          ? campaign.user_id === db.session.user.id
          : campaign.anonymous_session_id === db.anonymous_session_id,
      );
      return owned
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .map((campaign) => {
          // Seeded and never-opened campaigns have no assets yet, and the card
          // needs the feed ad to preview.
          ensureMaterialized(db, campaign);
          return summarize(db, campaign);
        });
    });
  },

  async saveProduct(campaignId: string, input: ProductInput): Promise<Product> {
    await delay(LATENCY.write);

    if (!input.name?.trim()) {
      throw new ApiError("validation_error", "اسم محصول رو بنویس.");
    }

    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const product = ensureProduct(db, campaign);
      const brand = brandOf(db, campaign);

      const incomingName = input.name.trim();
      const incomingDescription = blank(input.description);
      const incomingPrice = blank(input.price_text);
      const incomingBenefit = blank(input.main_benefit);
      const incomingBrand = blank(input.brand_name);

      let changed =
        incomingName !== (product.name || "") ||
        incomingDescription !== blank(product.description) ||
        incomingPrice !== blank(product.price_text) ||
        incomingBenefit !== blank(product.main_benefit);
      if (incomingBrand !== null) {
        changed = changed || incomingBrand !== (brand?.name ?? null);
      }

      product.name = incomingName;
      product.description = incomingDescription;
      product.price_text = incomingPrice;
      product.main_benefit = incomingBenefit;
      product.updated_at = nowIso();

      const brandName = incomingBrand;
      if (brandName) {
        const existing = db.brands.find(
          (brand) =>
            brand.name === brandName &&
            (brand.user_id === (db.session?.user.id ?? null) ||
              brand.id === campaign.brand_id),
        );
        if (existing) {
          campaign.brand_id = existing.id;
          product.brand_id = existing.id;
        } else {
          const brand: Brand = {
            id: newId("brd"),
            user_id: db.session?.user.id ?? null,
            name: brandName,
            description: null,
            category: null,
            instagram_handle: null,
            website: null,
            target_audience: null,
            tone: null,
            visual_style: campaign.visual_style,
            primary_color: null,
            secondary_color: null,
            created_at: nowIso(),
            updated_at: nowIso(),
          };
          db.brands.push(brand);
          campaign.brand_id = brand.id;
          product.brand_id = brand.id;
        }
      }

      dropStaleConcepts(db, campaign, changed);

      campaign.updated_at = nowIso();
      return { ...product };
    });
  },

  async uploadProductImages(
    campaignId: string,
    files: File[],
  ): Promise<ProductImage[]> {
    if (files.length === 0) return [];

    const storagePaths: string[] = [];
    for (const file of files) {
      storagePaths.push(await imageStore.putImage(file));
    }
    await delay(LATENCY.upload);

    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const product = ensureProduct(db, campaign);

      const existing = db.product_images.filter(
        (image) => image.product_id === product.id,
      );
      if (existing.length + storagePaths.length > 3) {
        throw new ApiError("validation_error", "حداکثر ۳ عکس می‌تونی اضافه کنی.");
      }

      const created = storagePaths.map((storagePath, index) => {
        const image: ProductImage = {
          id: newId("img"),
          product_id: product.id,
          storage_path: storagePath,
          is_primary: existing.length === 0 && index === 0,
          created_at: nowIso(),
        };
        return image;
      });

      db.product_images.push(...created);
      campaign.updated_at = nowIso();
      return created;
    });
  },

  async deleteProductImage(campaignId: string, imageId: string): Promise<void> {
    await delay(LATENCY.write);
    const storagePath = mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const image = db.product_images.find((item) => item.id === imageId);
      if (!image) throw new ApiError("not_found", "این عکس پیدا نشد.");

      db.product_images = db.product_images.filter((item) => item.id !== imageId);

      const remaining = db.product_images.filter(
        (item) => item.product_id === image.product_id,
      );
      if (image.is_primary && remaining.length > 0) {
        remaining[0].is_primary = true;
      }
      return image.storage_path;
    });

    if (storagePath.startsWith("local://")) {
      await imageStore.deleteImage(storagePath);
    }
  },

  async useSampleProduct(campaignId: string): Promise<ProductImage[]> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const product = ensureProduct(db, campaign);

      db.product_images = db.product_images.filter(
        (image) => image.product_id !== product.id,
      );

      const image: ProductImage = {
        id: newId("img"),
        product_id: product.id,
        storage_path: SAMPLE_IMAGE_PATH,
        is_primary: true,
        created_at: nowIso(),
      };
      db.product_images.push(image);

      // Prefill the brief so the demo path shows a complete example.
      product.name ||= "زعفران ممتاز";
      product.description ??= "زعفران یک گرمی مناسب هدیه";
      product.price_text ??= "۳۹۹ هزار تومان";
      product.main_benefit ??= "بسته‌بندی هدیه و کیفیت صادراتی";
      product.updated_at = nowIso();

      campaign.updated_at = nowIso();
      return [image];
    });
  },

  async generateConcepts(campaignId: string): Promise<CampaignConcept[]> {
    await delay(LATENCY.concepts);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      if (!campaign.objective || !campaign.visual_style) {
        throw new ApiError(
          "validation_error",
          "برای ساخت ایده، هدف و سبک تبلیغ رو انتخاب کن.",
        );
      }

      const round = (db.concept_rounds[campaign.id] ?? -1) + 1;
      db.concept_rounds[campaign.id] = round;

      const created = writeConcepts(
        db,
        campaign,
        buildConcepts(buildCopyContext(db, campaign)),
      );

      campaign.selected_concept_id = null;
      campaign.status = "concepts_ready";
      campaign.updated_at = nowIso();
      return created;
    });
  },

  async selectConcept(campaignId: string, conceptId: string): Promise<Campaign> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const concepts = conceptsOf(db, campaign.id);
      const target = concepts.find((concept) => concept.id === conceptId);
      if (!target) throw new ApiError("not_found", "این ایده پیدا نشد.");

      concepts.forEach((concept) => {
        concept.selected = concept.id === conceptId;
      });
      campaign.selected_concept_id = conceptId;
      campaign.status = "concept_selected";
      campaign.updated_at = nowIso();
      return { ...campaign };
    });
  },

  async startGeneration(campaignId: string): Promise<CampaignStatusResponse> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      if (!db.session) {
        throw new ApiError("unauthorized", "برای ساخت کمپین اول باید وارد بشی.");
      }
      if (!campaign.selected_concept_id) {
        throw new ApiError("validation_error", "اول یکی از ایده‌ها رو انتخاب کن.");
      }

      // Idempotency: repeated taps must not start a second job (spec §27).
      const active = db.generation_jobs.find(
        (job) =>
          job.campaign_id === campaign.id &&
          (job.status === "queued" || job.status === "processing"),
      );
      if (active || campaign.status === "generating" || campaign.status === "queued") {
        return statusResponse(campaign, "planning", 1, "کمپینت توی صف ساخته…");
      }
      if (campaign.status === "ready" || campaign.status === "partial_failed") {
        return statusResponse(campaign, null, 100, null);
      }

      db.generation_jobs.push({
        id: newId("job"),
        campaign_id: campaign.id,
        job_type: "campaign_generation",
        status: "queued",
        started_at: nowIso(),
        completed_at: null,
        error_message: null,
      });

      campaign.status = "queued";
      campaign.updated_at = nowIso();
      return statusResponse(campaign, null, 0, "کمپینت توی صف ساخته…");
    });
  },

  async getCampaignStatus(campaignId: string): Promise<CampaignStatusResponse> {
    await delay(LATENCY.read);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      if (
        campaign.status === "ready" ||
        campaign.status === "partial_failed" ||
        campaign.status === "failed"
      ) {
        ensureMaterialized(db, campaign);
        return statusResponse(
          campaign,
          null,
          campaign.status === "failed" ? 0 : 100,
          null,
          campaign.status === "partial_failed" ? ["story_final"] : [],
        );
      }

      const job = db.generation_jobs
        .filter((item) => item.campaign_id === campaign.id)
        .sort((a, b) => b.started_at.localeCompare(a.started_at))[0];

      if (!job || job.status === "succeeded") {
        return statusResponse(campaign, null, 0, null);
      }

      const elapsed = Date.now() - new Date(job.started_at).getTime();

      if (elapsed < QUEUE_DURATION_MS) {
        campaign.status = "queued";
        return statusResponse(campaign, null, 1, "کمپینت توی صف ساخته…");
      }

      const progress = computeGenerationProgress(elapsed - QUEUE_DURATION_MS);

      if (!progress.done) {
        campaign.status = "generating";
        job.status = "processing";
        return statusResponse(
          campaign,
          progress.stage,
          progress.percent,
          progress.message_fa,
        );
      }

      if (getFailureMode() === "generation") {
        job.status = "failed";
        job.completed_at = nowIso();
        job.error_message = "mock_generation_failure";
        campaign.status = "failed";
        campaign.updated_at = nowIso();
        return statusResponse(campaign, null, 0, null);
      }

      job.status = "succeeded";
      job.completed_at = nowIso();
      const finalStatus = materializeCampaign(db, campaign);

      return statusResponse(
        campaign,
        null,
        100,
        null,
        finalStatus === "partial_failed" ? ["story_final"] : [],
      );
    });
  },

  async updateCopy(
    campaignId: string,
    copyId: string,
    content: string,
  ): Promise<CampaignCopy> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const copy = db.campaign_copy.find(
        (item) => item.id === copyId && item.campaign_id === campaign.id,
      );
      if (!copy) throw new ApiError("not_found", "این متن پیدا نشد.");

      copy.content = content;
      copy.updated_at = nowIso();
      return { ...copy };
    });
  },

  async rewriteCopy(
    campaignId: string,
    copyId: string,
    intent: RewriteIntent,
  ): Promise<CampaignCopy> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const copy = db.campaign_copy.find(
        (item) => item.id === copyId && item.campaign_id === campaign.id,
      );
      if (!copy) throw new ApiError("not_found", "این متن پیدا نشد.");
      if (
        intent === "new_headline" ||
        !["informal", "shorter", "stronger_cta", "more_luxury"].includes(intent)
      ) {
        throw new ApiError("validation_error", "این تغییر برای این متن ممکن نیست.");
      }
      const product = db.products.find((item) => item.id === campaign.product_id);
      copy.content = stubRewrite(
        intent,
        copy.content,
        copy.copy_type,
        product?.name ?? "محصول شما",
      );
      copy.updated_at = nowIso();
      campaign.updated_at = nowIso();
      return { ...copy };
    });
  },

  async regenerateAsset(
    campaignId: string,
    assetId: string,
  ): Promise<CampaignAsset> {
    await delay(LATENCY.upload);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const asset = db.campaign_assets.find(
        (item) => item.id === assetId && item.campaign_id === campaign.id,
      );
      if (!asset) throw new ApiError("not_found", "این تصویر پیدا نشد.");

      const spec = asset.metadata_json as AssetRenderSpec;
      const options = backgroundsForStyle(campaign.visual_style ?? "modern");
      const currentIndex = options.findIndex(
        (background) => background.id === spec.background_id,
      );
      const next = options[(currentIndex + 1) % options.length];

      asset.metadata_json = { ...spec, background_id: next.id, failed: false };

      // Retrying the failed asset repairs the campaign as a whole.
      if (campaign.status === "partial_failed") {
        const stillFailing = db.campaign_assets.some(
          (item) =>
            item.campaign_id === campaign.id &&
            (item.metadata_json as AssetRenderSpec).failed,
        );
        if (!stillFailing) campaign.status = "ready";
      }

      campaign.updated_at = nowIso();
      return { ...asset };
    });
  },

  async updateAssetText(
    campaignId: string,
    assetId: string,
    patch: AssetTextPatch,
  ): Promise<CampaignAsset> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      const asset = db.campaign_assets.find(
        (item) => item.id === assetId && item.campaign_id === campaign.id,
      );
      if (!asset) throw new ApiError("not_found", "این تصویر پیدا نشد.");

      asset.metadata_json = { ...(asset.metadata_json as AssetRenderSpec), ...patch };
      campaign.updated_at = nowIso();
      return { ...asset };
    });
  },

  async rewriteAssetText(
    campaignId: string,
    assetId: string,
    intent: RewriteIntent,
  ): Promise<CampaignAsset> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const asset = db.campaign_assets.find(
        (item) => item.id === assetId && item.campaign_id === campaign.id,
      );
      if (!asset) throw new ApiError("not_found", "این تصویر پیدا نشد.");
      if (intent !== "new_headline" && intent !== "stronger_cta") {
        throw new ApiError("validation_error", "این تغییر برای این متن ممکن نیست.");
      }
      const spec = { ...(asset.metadata_json as AssetRenderSpec) };
      const product = db.products.find((item) => item.id === campaign.product_id);
      const productName = product?.name ?? "محصول شما";
      if (intent === "new_headline") {
        spec.headline_fa = stubRewrite(intent, spec.headline_fa, "headline", productName);
      } else {
        spec.cta_fa = stubRewrite(intent, spec.cta_fa ?? "", "cta", productName);
        const ctaCopy = db.campaign_copy.find(
          (item) => item.campaign_id === campaign.id && item.copy_type === "cta",
        );
        if (ctaCopy) {
          ctaCopy.content = spec.cta_fa ?? ctaCopy.content;
          ctaCopy.updated_at = nowIso();
        }
      }
      asset.metadata_json = spec;
      campaign.updated_at = nowIso();
      return { ...asset };
    });
  },

  async listBrands(): Promise<Brand[]> {
    await delay(LATENCY.read);
    const db = readDb();
    const userId = db.session?.user.id ?? null;
    return db.brands.filter((brand) => brand.user_id === userId);
  },

  async createBrand(input: BrandInput): Promise<Brand> {
    await delay(LATENCY.write);
    if (!input.name?.trim()) {
      throw new ApiError("validation_error", "اسم برند رو بنویس.");
    }
    return mutateDb((db) => {
      const brand: Brand = {
        id: newId("brd"),
        user_id: db.session?.user.id ?? null,
        name: input.name.trim(),
        description: input.description ?? null,
        category: input.category ?? null,
        instagram_handle: input.instagram_handle ?? null,
        website: input.website ?? null,
        target_audience: input.target_audience ?? null,
        tone: input.tone ?? null,
        visual_style: input.visual_style ?? null,
        primary_color: input.primary_color ?? null,
        secondary_color: input.secondary_color ?? null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      db.brands.push(brand);
      return brand;
    });
  },

  async getBrand(brandId: string): Promise<Brand> {
    await delay(LATENCY.read);
    const db = readDb();
    const brand = db.brands.find((item) => item.id === brandId);
    if (!brand) throw new ApiError("not_found", "این برند پیدا نشد.");
    if (brand.user_id && brand.user_id !== db.session?.user.id) {
      throw new ApiError("unauthorized", "دسترسی به این برند مجاز نیست.");
    }
    return brand;
  },

  async updateBrand(brandId: string, patch: BrandInput): Promise<Brand> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const brand = db.brands.find((item) => item.id === brandId);
      if (!brand) throw new ApiError("not_found", "این برند پیدا نشد.");
      if (brand.user_id && brand.user_id !== db.session?.user.id) {
        throw new ApiError("unauthorized", "دسترسی به این برند مجاز نیست.");
      }

      Object.assign(brand, {
        name: patch.name?.trim() || brand.name,
        description: patch.description ?? brand.description,
        category: patch.category ?? brand.category,
        instagram_handle: patch.instagram_handle ?? brand.instagram_handle,
        website: patch.website ?? brand.website,
        target_audience: patch.target_audience ?? brand.target_audience,
        tone: patch.tone ?? brand.tone,
        visual_style: patch.visual_style ?? brand.visual_style,
        primary_color: patch.primary_color ?? brand.primary_color,
        secondary_color: patch.secondary_color ?? brand.secondary_color,
        updated_at: nowIso(),
      });
      return { ...brand };
    });
  },

  async requestEmailCode(input: EmailCodeRequest): Promise<void> {
    await delay(LATENCY.auth);
    if (!isEmail(input.email)) {
      throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
    }
    // No mail is sent in mock mode; verifyEmailCode accepts any six digits.
  },

  async verifyEmailCode(input: EmailCodeVerification): Promise<Session> {
    await delay(LATENCY.auth);
    if (!/^\d{6}$/.test(input.code.trim())) {
      throw new ApiError("validation_error", "کد ۶ رقمی رو کامل وارد کن.");
    }
    return createMockSession(input.email);
  },

  async signInWithGoogle(): Promise<void> {
    await delay(LATENCY.auth);
    // Mock mode has no OAuth provider, so this signs in directly under a
    // stand-in address rather than pretending to leave the app.
    createMockSession("user@gmail.com");
  },

  async adoptAnonymousWork(): Promise<Session> {
    const session = readDb().session;
    if (!session) {
      throw new ApiError("unauthorized", "برای ساخت کمپین اول باید وارد بشی.");
    }
    return session;
  },

  async signOut(): Promise<void> {
    await delay(LATENCY.write);
    const db = readDb();
    db.session = null;
    writeDb(db);
  },

  async getSession(): Promise<Session | null> {
    return readDb().session;
  },

  async resolveAssetUrl(storagePath: string | null): Promise<string | null> {
    if (!storagePath) return null;
    if (storagePath.startsWith("public://")) {
      return `/${storagePath.slice("public://".length)}`;
    }
    if (storagePath.startsWith("local://")) {
      return imageStore.getImageUrl(storagePath);
    }
    return storagePath;
  },

  async resolveAssetUrls(
    storagePaths: string[],
  ): Promise<Record<string, string | null>> {
    const entries = await Promise.all(
      storagePaths.map(
        async (path) => [path, await mockApi.resolveAssetUrl(path)] as const,
      ),
    );
    return Object.fromEntries(entries);
  },
};

function stubRewrite(
  intent: RewriteIntent,
  current: string,
  field: string,
  productName: string,
): string {
  const text = current.trim();
  if (intent === "shorter") {
    const first = text.split("\n")[0]?.trim() ?? text;
    return first !== text ? first : text.slice(0, Math.max(12, Math.floor(text.length / 2)));
  }
  if (intent === "informal") {
    return text.includes("😊") ? text : `${text}\nخوشحال می‌شیم کمکت کنیم 😊`;
  }
  if (intent === "stronger_cta") {
    return field === "cta" ? "همین حالا سفارش بده" : `${text}\nهمین حالا سفارش بده 👇`;
  }
  if (intent === "new_headline") {
    return `${productName}، انتخاب هوشمندانه‌تر`;
  }
  if (intent === "more_luxury") {
    return `مجموعه‌ای منتخب\n${text}`;
  }
  return text;
}
