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
  CropRect,
  EducationalPost,
  EducationalPostStatusResponse,
  EducationalPostSummary,
  EducationalTheme,
  EducationalThemeList,
  EducationalThemeSpec,
  GenerationStage,
  Product,
  ProductImage,
  Session,
  VisualCandidate,
} from "@/types/domain";
import {
  ApiError,
  type AfarinApi,
  type AssetTextPatch,
  type BrandInput,
  type CreateCampaignInput,
  type CreateEducationalPostInput,
  type ProductInput,
  type EmailCodeRequest,
  type EmailCodeVerification,
  type EmailPasswordCredentials,
  type PasswordResetRequest,
  type RewriteIntent,
  type SaveEducationalThemeInput,
  type UpdateCampaignInput,
  type UpdatePasswordInput,
} from "@/lib/api/types";
import { backgroundsForStyle } from "@/lib/content/backgrounds";
import * as imageStore from "@/lib/storage/imageStore";
import { FULL_CROP } from "@/features/campaign/wizard/cropMath";
import {
  applyRoleText,
  parseTextLayers,
  specWithLayers,
  syncContentFieldsFromLayers,
  TextLayerValidationError,
} from "@/features/campaign/ad-renderer/textLayers";
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
import {
  BUILTIN_EDUCATION_THEMES,
  buildEducationalRenderSpec,
  buildEducationalResult,
  designedTheme,
  listingHeadline,
  sanitizeEducationalTheme,
} from "./fixtures/education";
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
  type MockEducationalPost,
  type MockEducationalTheme,
} from "./mockDb";

const QUEUE_DURATION_MS = 900;

/* --- Educational content -------------------------------------------------- */

const MAX_EDUCATION_PROMPT = 2000;
const EDUCATION_IMAGE_PATH = "public://mock/education-scene.svg";

/**
 * One agent call then one image, so the run is shorter than an advertising
 * campaign's five assets.
 */
const EDUCATION_STAGES: readonly {
  stage: GenerationStage;
  duration_ms: number;
  message_fa: string;
}[] = [
  { stage: "planning", duration_ms: 2200, message_fa: "در حال طراحی پست…" },
  { stage: "visual", duration_ms: 6000, message_fa: "در حال ساخت تصویر…" },
  { stage: "finalizing", duration_ms: 1200, message_fa: "تقریباً آماده‌ست…" },
];

const EDUCATION_TOTAL_MS = EDUCATION_STAGES.reduce(
  (total, item) => total + item.duration_ms,
  0,
);

function computeEducationProgress(elapsedMs: number): {
  stage: GenerationStage;
  percent: number;
  message_fa: string;
  done: boolean;
} {
  const elapsed = Math.max(0, elapsedMs);
  if (elapsed >= EDUCATION_TOTAL_MS) {
    const last = EDUCATION_STAGES[EDUCATION_STAGES.length - 1];
    return { stage: last.stage, percent: 100, message_fa: last.message_fa, done: true };
  }
  let consumed = 0;
  for (const item of EDUCATION_STAGES) {
    if (elapsed < consumed + item.duration_ms) {
      return {
        stage: item.stage,
        percent: Math.min(99, Math.round((elapsed / EDUCATION_TOTAL_MS) * 100)),
        message_fa: item.message_fa,
        done: false,
      };
    }
    consumed += item.duration_ms;
  }
  const last = EDUCATION_STAGES[EDUCATION_STAGES.length - 1];
  return { stage: last.stage, percent: 100, message_fa: last.message_fa, done: true };
}

/** Educational content is authenticated-only, so there is no anonymous owner. */
function requireEducationUser(db: MockDbShape): string {
  const userId = db.session?.user.id;
  if (!userId) {
    throw new ApiError("unauthorized", "برای ساخت پست آموزشی اول باید وارد بشی.");
  }
  return userId;
}

function findEducationalPost(
  db: MockDbShape,
  postId: string,
): MockEducationalPost {
  const userId = requireEducationUser(db);
  const post = db.educational_posts.find((item) => item.id === postId);
  if (!post) throw new ApiError("not_found", "این پست آموزشی پیدا نشد.");
  if (post.user_id !== userId) {
    throw new ApiError("unauthorized", "دسترسی به این پست برای شما مجاز نیست.");
  }
  return post;
}

function findEducationalTheme(
  db: MockDbShape,
  themeId: string,
): MockEducationalTheme {
  const userId = requireEducationUser(db);
  const theme = db.educational_themes.find((item) => item.id === themeId);
  if (!theme) throw new ApiError("not_found", "این تم پیدا نشد.");
  if (theme.user_id !== userId) {
    throw new ApiError("unauthorized", "دسترسی به این تم برای شما مجاز نیست.");
  }
  return theme;
}

/** Public shape: the owner column never leaves the mock. */
function themeOut(theme: MockEducationalTheme): EducationalTheme {
  const { user_id: _ownerId, ...rest } = theme;
  return rest;
}

function postOut(post: MockEducationalPost): EducationalPost {
  const { user_id: _ownerId, ...rest } = post;
  return rest;
}

function resolveMockTheme(
  db: MockDbShape,
  userId: string,
  input: CreateEducationalPostInput,
): EducationalThemeSpec | null {
  if (input.theme_id) {
    const saved = db.educational_themes.find(
      (item) => item.id === input.theme_id && item.user_id === userId,
    );
    if (!saved) throw new ApiError("not_found", "این تم پیدا نشد.");
    return saved.theme_json;
  }
  if (input.builtin_theme_id) {
    const builtin = BUILTIN_EDUCATION_THEMES.find(
      (item) => item.id === input.builtin_theme_id,
    );
    if (!builtin) throw new ApiError("not_found", "این تم پیدا نشد.");
    const { id: _id, source: _source, ...spec } = builtin;
    return spec;
  }
  return null;
}

function educationStatus(post: EducationalPost): EducationalPostStatusResponse {
  if (post.status === "ready") {
    return {
      post_id: post.id,
      status: post.status,
      stage: null,
      percent: 100,
      message_fa: null,
    };
  }
  if (post.status === "failed") {
    return {
      post_id: post.id,
      status: post.status,
      stage: null,
      percent: 0,
      message_fa: post.error_message ?? "ساخت پست انجام نشد.",
    };
  }
  return {
    post_id: post.id,
    status: post.status,
    stage: "planning",
    percent: 5,
    message_fa: "در نوبت ساخت…",
  };
}

function finishEducationalPost(
  post: MockEducationalPost,
  elapsedMs: number,
): void {
  if (getFailureMode() === "generation") {
    post.status = "failed";
    post.error_message = "ساخت پست انجام نشد. یک بار دیگه امتحان کن.";
    post.updated_at = nowIso();
    return;
  }
  const selected = post.theme_json as EducationalThemeSpec;
  const theme = selected.illustration_style
    ? selected
    : designedTheme(post.user_prompt);
  const result = buildEducationalResult(post.user_prompt, theme);
  post.language = result.language;
  post.headline = listingHeadline(post.user_prompt);
  post.agent_json = result;
  post.theme_json = theme;
  post.image_storage_path = EDUCATION_IMAGE_PATH;
  post.render_spec_json = buildEducationalRenderSpec(EDUCATION_IMAGE_PATH);
  post.wall_time_ms = Math.round(elapsedMs);
  post.status = "ready";
  post.updated_at = nowIso();
}

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
  return primary?.crop_storage_path || primary?.storage_path || null;
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

const DIRECTION_PAIRS = [
  [
    {
      style_id: "photoreal_commercial",
      template_id: "hero_product",
      angle: "editorial hero",
    },
    {
      style_id: "anime",
      template_id: "illustrated_scene",
      angle: "illustrated lifestyle",
    },
    {
      style_id: "surreal",
      template_id: "giant_miniature_world",
      angle: "surreal scale",
    },
  ],
  [
    {
      style_id: "fashion_editorial",
      template_id: "magazine_cover",
      angle: "fashion editorial",
    },
    {
      style_id: "watercolor_illustration",
      template_id: "flat_lay",
      angle: "watercolor story",
    },
    {
      style_id: "neon",
      template_id: "cinematic_environment",
      angle: "neon night",
    },
  ],
] as const;

function writeConcepts(
  db: MockDbShape,
  campaign: Campaign,
  fixtures: ConceptFixture[],
  round = 0,
): CampaignConcept[] {
  db.campaign_concepts = db.campaign_concepts.filter(
    (concept) => concept.campaign_id !== campaign.id,
  );

  const pairs = DIRECTION_PAIRS[round % DIRECTION_PAIRS.length];
  const created = fixtures.map((fixture, index) => {
    const pair = pairs[index] ?? pairs[0];
    const concept: CampaignConcept = {
      id: newId("cnc"),
      campaign_id: campaign.id,
      concept_number: index + 1,
      title_fa: fixture.title_fa,
      headline_fa: fixture.headline_fa,
      description_fa: fixture.description_fa,
      visual_direction: fixture.visual_direction,
      background_prompt: fixture.background_prompt,
      raw_json: {
        background_id: fixture.background_id,
        style_id: pair.style_id,
        template_id: pair.template_id,
        angle: pair.angle,
        identity_constraints: ["keep major colors", "keep silhouette"],
        image_direction: fixture.visual_direction,
        text_safe_area: "bottom",
      },
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
    scene_image_path: null,
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

  db.visual_candidates = db.visual_candidates.filter(
    (item) => item.campaign_id !== campaign.id,
  );
  const count = campaign.requested_image_count === 3 ? 3 : 1;
  const productPath = primaryImagePath(db, campaign) ?? SAMPLE_IMAGE_PATH;
  for (let slot = 1; slot <= count; slot += 1) {
    const candidate: VisualCandidate & { campaign_id: string } = {
      id: newId("vis"),
      campaign_id: campaign.id,
      slot,
      kind: "primary",
      storage_path: productPath,
      hard_failed: false,
      hidden: false,
      created_at: nowIso(),
    };
    db.visual_candidates.push(candidate);
  }

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
        requested_image_count: 1,
        visual_instruction: null,
        selected_template_id: null,
        visual_recipe_json: {},
        current_visual_attempt_id: null,
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
        visual_attempt: null,
        visual_candidates: db.visual_candidates.filter(
          (item) => item.campaign_id === campaign.id,
        ),
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
      if (patch.requested_image_count !== undefined) {
        campaign.requested_image_count = patch.requested_image_count;
      }
      if (patch.visual_instruction !== undefined) {
        campaign.visual_instruction = patch.visual_instruction;
      }
      if (patch.selected_template_id !== undefined) {
        campaign.selected_template_id = patch.selected_template_id;
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
          crop: { ...FULL_CROP },
          crop_storage_path: null,
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
        crop: { ...FULL_CROP },
        crop_storage_path: null,
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

  async updateProductCrop(
    campaignId: string,
    imageId: string,
    crop: CropRect,
  ): Promise<ProductImage> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const image = db.product_images.find((item) => item.id === imageId);
      if (!image) throw new ApiError("not_found", "این عکس پیدا نشد.");
      if (crop.width < 0.12 || crop.height < 0.12) {
        throw new ApiError(
          "validation_error",
          "کادر محصول رو یک مقدار بزرگ‌تر انتخاب کن.",
        );
      }
      image.crop = crop;
      campaign.updated_at = nowIso();
      return { ...image };
    });
  },

  async getVisualCatalog() {
    const response = await fetch("/visual-previews/catalog.json");
    if (!response.ok) {
      return { templates: [] };
    }
    const raw = (await response.json()) as {
      styles?: { id: string; label_fa: string; description_fa: string; preview_path: string }[];
      templates?: { id: string; label_fa: string; description_fa: string; preview_path: string }[];
    };
    if (raw.styles?.length) {
      return { templates: [...raw.styles, ...(raw.templates ?? [])] };
    }
    return { templates: raw.templates ?? [] };
  },

  async focusVisualCandidate(campaignId: string, candidateId: string) {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);
      const candidate = db.visual_candidates.find(
        (item) => item.id === candidateId && item.campaign_id === campaign.id,
      );
      if (!candidate) throw new ApiError("not_found", "این تصویر پیدا نشد.");
      campaign.status = "ready";
      campaign.updated_at = nowIso();
      const feed = db.campaign_assets.find(
        (asset) => asset.campaign_id === campaign.id && asset.asset_type === "feed_final",
      );
      if (feed) {
        feed.metadata_json = {
          ...(feed.metadata_json as object),
          concept_slot: candidate.slot,
          scene_image_path: candidate.storage_path,
        };
      }
      return { ...campaign };
    });
  },

  async regenerateVisuals(campaignId: string) {
    await delay(LATENCY.write);
    const campaign = findCampaign(readDb(), campaignId);
    assertOwnership(readDb(), campaign);
    return {
      campaign_id: campaignId,
      status: "ready" as const,
      stage: null,
      percent: 100,
      message_fa: null,
      failed_asset_types: [],
    };
  },

  async startGeneration(campaignId: string): Promise<CampaignStatusResponse> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const campaign = findCampaign(db, campaignId);
      assertOwnership(db, campaign);

      if (!db.session) {
        throw new ApiError("unauthorized", "برای ساخت کمپین اول باید وارد بشی.");
      }
      if (!campaign.objective || !campaign.visual_style) {
        throw new ApiError("validation_error", "اول هدف و حس تبلیغ رو انتخاب کن.");
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
      if (
        campaign.status === "ready" ||
        campaign.status === "partial_failed"
      ) {
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

      let spec = { ...(asset.metadata_json as AssetRenderSpec) };
      const { text_layers: nextLayers, ...copyPatch } = patch;
      spec = { ...spec, ...copyPatch };
      if (copyPatch.headline_fa !== undefined && spec.text_layers) {
        spec = {
          ...spec,
          text_layers: applyRoleText(
            spec.text_layers,
            "headline",
            copyPatch.headline_fa,
          ),
        };
      }
      if (copyPatch.cta_fa !== undefined && spec.text_layers) {
        spec = {
          ...spec,
          text_layers: applyRoleText(spec.text_layers, "cta", copyPatch.cta_fa ?? ""),
        };
      }
      if (copyPatch.subheadline_fa !== undefined && spec.text_layers) {
        spec = {
          ...spec,
          text_layers: applyRoleText(
            spec.text_layers,
            "subheadline",
            copyPatch.subheadline_fa ?? "",
          ),
        };
      }
      if (copyPatch.price_text !== undefined && spec.text_layers) {
        spec = {
          ...spec,
          text_layers: applyRoleText(
            spec.text_layers,
            "price",
            copyPatch.price_text ?? "",
          ),
        };
      }
      if ("text_layers" in patch) {
        if (nextLayers === null) {
          spec = specWithLayers(spec, null);
        } else {
          try {
            const layers = parseTextLayers(nextLayers);
            spec = syncContentFieldsFromLayers(specWithLayers(spec, layers), layers);
          } catch (caught) {
            if (caught instanceof TextLayerValidationError && caught.code === "too_many") {
              throw new ApiError(
                "validation_error",
                "حداکثر ۱۰ متن می‌تونی به این تصویر اضافه کنی.",
              );
            }
            throw new ApiError("validation_error", "این ویرایش متن معتبر نیست.");
          }
        }
      }
      asset.metadata_json = spec;
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
        if (spec.text_layers) {
          spec.text_layers = applyRoleText(spec.text_layers, "headline", spec.headline_fa);
        }
      } else {
        spec.cta_fa = stubRewrite(intent, spec.cta_fa ?? "", "cta", productName);
        if (spec.text_layers) {
          spec.text_layers = applyRoleText(spec.text_layers, "cta", spec.cta_fa ?? "");
        }
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

  async createEducationalPost(
    input: CreateEducationalPostInput,
  ): Promise<EducationalPost> {
    await delay(LATENCY.write);
    const prompt = (input.user_prompt ?? "").trim();
    if (!prompt) {
      throw new ApiError("validation_error", "بنویس چه پستی می‌خوای بسازم.");
    }
    if (prompt.length > MAX_EDUCATION_PROMPT) {
      throw new ApiError("validation_error", "توضیحت خیلی بلنده. کوتاه‌ترش کن.");
    }
    return mutateDb((db) => {
      const userId = requireEducationUser(db);
      const theme = resolveMockTheme(db, userId, input);
      const post: MockEducationalPost = {
        id: newId("edu"),
        user_id: userId,
        user_prompt: prompt,
        selected_theme_id: input.theme_id ?? null,
        selected_builtin_theme_id: input.builtin_theme_id ?? null,
        language: null,
        headline: null,
        status: "queued",
        error_message: null,
        image_storage_path: null,
        agent_json: {},
        // Holds the selected theme until generation replaces it with the
        // effective one, mirroring the backend.
        theme_json: theme ?? {},
        render_spec_json: {},
        wall_time_ms: null,
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      db.educational_posts.push(post);
      return postOut(post);
    });
  },

  async getEducationalPost(postId: string): Promise<EducationalPost> {
    await delay(LATENCY.read);
    const db = readDb();
    return postOut(findEducationalPost(db, postId));
  },

  async listEducationalPosts(): Promise<EducationalPostSummary[]> {
    await delay(LATENCY.read);
    const db = readDb();
    const userId = db.session?.user.id;
    if (!userId) return [];
    return db.educational_posts
      .filter((post) => post.user_id === userId)
      .reverse()
      .map((post) => ({
        id: post.id,
        headline: post.headline,
        status: post.status,
        language: post.language,
        image_storage_path: post.image_storage_path,
        created_at: post.created_at,
      }));
  },

  async getEducationalPostStatus(
    postId: string,
  ): Promise<EducationalPostStatusResponse> {
    await delay(LATENCY.read);
    return mutateDb((db) => {
      const post = findEducationalPost(db, postId);
      if (post.status === "ready" || post.status === "failed") {
        return educationStatus(post);
      }

      const elapsed = Date.now() - new Date(post.created_at).getTime();
      const progress = computeEducationProgress(elapsed);
      if (!progress.done) {
        post.status = "generating";
        post.updated_at = nowIso();
        return {
          post_id: post.id,
          status: post.status,
          stage: progress.stage,
          percent: progress.percent,
          message_fa: progress.message_fa,
        };
      }

      finishEducationalPost(post, elapsed);
      return educationStatus(post);
    });
  },

  async deleteEducationalPost(postId: string): Promise<void> {
    await delay(LATENCY.write);
    mutateDb((db) => {
      const post = findEducationalPost(db, postId);
      db.educational_posts = db.educational_posts.filter(
        (item) => item.id !== post.id,
      );
      return null;
    });
  },

  async listEducationalThemes(): Promise<EducationalThemeList> {
    await delay(LATENCY.read);
    const db = readDb();
    const userId = db.session?.user.id;
    return {
      builtin: BUILTIN_EDUCATION_THEMES.map((theme) => ({ ...theme })),
      saved: db.educational_themes
        .filter((row) => row.user_id === userId)
        .map(themeOut),
    };
  },

  async saveEducationalTheme(
    input: SaveEducationalThemeInput,
  ): Promise<EducationalTheme> {
    await delay(LATENCY.write);
    return mutateDb((db) => {
      const userId = requireEducationUser(db);
      const post = findEducationalPost(db, input.post_id);
      const source = post.theme_json as EducationalThemeSpec;
      if (!source.illustration_style) {
        throw new ApiError(
          "validation_error",
          "برای این پست تمی برای ذخیره وجود نداره.",
        );
      }
      const name =
        (input.name ?? "").trim() ||
        source.name ||
        post.headline ||
        "تم آموزشی";
      const theme: MockEducationalTheme = {
        id: newId("edth"),
        user_id: userId,
        name,
        source: "user",
        theme_json: sanitizeEducationalTheme(source, name),
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      db.educational_themes.push(theme);
      return themeOut(theme);
    });
  },

  async renameEducationalTheme(
    themeId: string,
    name: string,
  ): Promise<EducationalTheme> {
    await delay(LATENCY.write);
    const trimmed = name.trim();
    if (!trimmed) {
      throw new ApiError("validation_error", "برای تم یک اسم بنویس.");
    }
    return mutateDb((db) => {
      const theme = findEducationalTheme(db, themeId);
      theme.name = trimmed;
      theme.theme_json = { ...theme.theme_json, name: trimmed };
      theme.updated_at = nowIso();
      return themeOut(theme);
    });
  },

  async deleteEducationalTheme(themeId: string): Promise<void> {
    await delay(LATENCY.write);
    mutateDb((db) => {
      const theme = findEducationalTheme(db, themeId);
      db.educational_themes = db.educational_themes.filter(
        (item) => item.id !== theme.id,
      );
      return null;
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

  async signInWithPassword(input: EmailPasswordCredentials): Promise<Session> {
    await delay(LATENCY.auth);
    if (!isEmail(input.email)) {
      throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
    }
    if (input.password.length < 8) {
      throw new ApiError("validation_error", "رمز باید حداقل ۸ حرف باشه.");
    }
    const email = input.email.trim().toLowerCase();
    const db = readDb();
    const stored = db.account_passwords[email];
    if (stored !== input.password) {
      throw new ApiError("validation_error", "ایمیل یا رمز درست نیست.");
    }
    return createMockSession(email);
  },

  async signUpWithPassword(input: EmailPasswordCredentials): Promise<Session> {
    await delay(LATENCY.auth);
    if (!isEmail(input.email)) {
      throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
    }
    if (input.password.length < 8) {
      throw new ApiError("validation_error", "رمز باید حداقل ۸ حرف باشه.");
    }
    const email = input.email.trim().toLowerCase();
    mutateDb((db) => {
      db.account_passwords[email] = input.password;
    });
    return createMockSession(email);
  },

  async requestPasswordReset(input: PasswordResetRequest): Promise<void> {
    await delay(LATENCY.auth);
    if (!isEmail(input.email)) {
      throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
    }
    mutateDb((db) => {
      db.pending_password_reset = input.email.trim().toLowerCase();
    });
  },

  async ensurePasswordRecoverySession(): Promise<void> {
    const db = readDb();
    if (db.pending_password_reset || db.session) return;
    throw new ApiError(
      "unauthorized",
      "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
    );
  },

  async updatePassword(input: UpdatePasswordInput): Promise<Session> {
    await delay(LATENCY.auth);
    if (input.password.length < 8) {
      throw new ApiError("validation_error", "رمز باید حداقل ۸ حرف باشه.");
    }
    const db = readDb();
    const email = db.pending_password_reset ?? db.session?.user.email ?? null;
    if (!email) {
      throw new ApiError(
        "unauthorized",
        "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
      );
    }
    mutateDb((state) => {
      state.account_passwords[email] = input.password;
      state.pending_password_reset = null;
    });
    return createMockSession(email);
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
