import type {
  Brand,
  Campaign,
  CampaignAsset,
  CampaignConcept,
  CampaignCopy,
  CampaignDetail,
  CampaignObjective,
  CampaignStatusResponse,
  CampaignSummary,
  CropRect,
  Product,
  ProductImage,
  Session,
  VisualStyle,
} from "@/types/domain";

/**
 * The single boundary between the UI and "the server".
 *
 * Every method corresponds 1:1 to an endpoint in docs/MVP_SPEC.md §24 and is
 * async, so swapping the Phase 1 mock for an HTTP client that talks to FastAPI
 * requires no changes above this file.
 */
export interface AfarinApi {
  // POST /api/campaigns
  createCampaign(input: CreateCampaignInput): Promise<Campaign>;
  // GET /api/campaigns/{id}
  getCampaign(campaignId: string): Promise<CampaignDetail>;
  // PATCH /api/campaigns/{id}
  updateCampaign(
    campaignId: string,
    patch: UpdateCampaignInput,
  ): Promise<Campaign>;
  // GET /api/campaigns
  listCampaigns(): Promise<CampaignSummary[]>;

  // POST /api/campaigns/{id}/product
  saveProduct(campaignId: string, input: ProductInput): Promise<Product>;
  // POST /api/campaigns/{id}/images
  uploadProductImages(
    campaignId: string,
    files: File[],
  ): Promise<ProductImage[]>;
  // DELETE /api/campaigns/{id}/images/{image_id}
  deleteProductImage(campaignId: string, imageId: string): Promise<void>;
  // POST /api/campaigns/{id}/images/sample
  useSampleProduct(campaignId: string): Promise<ProductImage[]>;
  // PATCH /api/campaigns/{id}/images/{image_id}/crop
  updateProductCrop(
    campaignId: string,
    imageId: string,
    crop: CropRect,
  ): Promise<ProductImage>;

  // POST /api/campaigns/{id}/concepts/generate
  generateConcepts(campaignId: string): Promise<CampaignConcept[]>;
  // POST /api/campaigns/{id}/concepts/{concept_id}/select
  selectConcept(campaignId: string, conceptId: string): Promise<Campaign>;

  // POST /api/campaigns/{id}/generate
  startGeneration(campaignId: string): Promise<CampaignStatusResponse>;
  // GET /api/campaigns/{id}/status
  getCampaignStatus(campaignId: string): Promise<CampaignStatusResponse>;

  // PATCH /api/campaigns/{id}/copy/{copy_id}
  updateCopy(
    campaignId: string,
    copyId: string,
    content: string,
  ): Promise<CampaignCopy>;
  // POST /api/campaigns/{id}/copy/{copy_id}/rewrite
  rewriteCopy(
    campaignId: string,
    copyId: string,
    intent: RewriteIntent,
  ): Promise<CampaignCopy>;
  // POST /api/campaigns/{id}/assets/{asset_id}/regenerate
  regenerateAsset(campaignId: string, assetId: string): Promise<CampaignAsset>;
  // PATCH /api/campaigns/{id}/assets/{asset_id}
  updateAssetText(
    campaignId: string,
    assetId: string,
    patch: AssetTextPatch,
  ): Promise<CampaignAsset>;
  // POST /api/campaigns/{id}/assets/{asset_id}/rewrite
  rewriteAssetText(
    campaignId: string,
    assetId: string,
    intent: RewriteIntent,
  ): Promise<CampaignAsset>;

  // GET /api/brands
  listBrands(): Promise<Brand[]>;
  // POST /api/brands
  createBrand(input: BrandInput): Promise<Brand>;
  // GET /api/brands/{id}
  getBrand(brandId: string): Promise<Brand>;
  // PATCH /api/brands/{id}
  updateBrand(brandId: string, patch: BrandInput): Promise<Brand>;

  /**
   * Auth, delegated to Supabase.
   *
   * Email sign-in is two calls because a real provider has to actually deliver
   * the code: `requestEmailCode` sends it, `verifyEmailCode` exchanges it for a
   * session. Phase 1's single `signUp` could not express the wait. This is the
   * one place Phase 2 changes the UX, and only by one screen.
   *
   * Completing either flow also transfers whatever the visitor built while
   * anonymous to the new account (spec §11).
   */
  requestEmailCode(input: EmailCodeRequest): Promise<void>;
  verifyEmailCode(input: EmailCodeVerification): Promise<Session>;
  /**
   * Google leaves the app entirely, so this resolves only if the redirect
   * cannot be started. Adoption happens at /auth/callback on the way back.
   */
  signInWithGoogle(input: GoogleSignInInput): Promise<void>;
  /** Claims the anonymous campaign for whoever is signed in now. */
  adoptAnonymousWork(): Promise<Session>;
  signOut(): Promise<void>;
  getSession(): Promise<Session | null>;

  /**
   * Turns an opaque `storage_path` into something an <img> can display: a
   * short-lived signed URL for private objects, a static path for the assets
   * that ship with the app (spec §27).
   */
  resolveAssetUrl(storagePath: string | null): Promise<string | null>;
  /**
   * Batched form. A results page shows five assets at once, and one request per
   * image would visibly stagger the reveal.
   */
  resolveAssetUrls(storagePaths: string[]): Promise<Record<string, string | null>>;
}

export interface CreateCampaignInput {
  brand_id?: string | null;
}

export interface UpdateCampaignInput {
  objective?: CampaignObjective | null;
  audience?: string | null;
  visual_style?: VisualStyle | null;
  brand_id?: string | null;
}

export interface ProductInput {
  name: string;
  description?: string | null;
  price_text?: string | null;
  main_benefit?: string | null;
  brand_name?: string | null;
}

export interface AssetTextPatch {
  headline_fa?: string;
  subheadline_fa?: string | null;
  cta_fa?: string | null;
  price_text?: string | null;
}

export type RewriteIntent =
  | "informal"
  | "shorter"
  | "stronger_cta"
  | "new_headline"
  | "more_luxury";

export interface BrandInput {
  name: string;
  description?: string | null;
  category?: string | null;
  instagram_handle?: string | null;
  website?: string | null;
  target_audience?: string | null;
  tone?: string | null;
  visual_style?: VisualStyle | null;
  primary_color?: string | null;
  secondary_color?: string | null;
}

export interface EmailCodeRequest {
  email: string;
}

export interface EmailCodeVerification {
  email: string;
  code: string;
}

export interface GoogleSignInInput {
  /** Absolute URL Supabase returns to once Google is done. */
  redirect_to: string;
}

export type ApiErrorCode =
  | "not_found"
  | "validation_error"
  | "unauthorized"
  | "conflict"
  | "upload_failed"
  | "generation_failed"
  | "rate_limited"
  | "unknown";

/**
 * Errors carry a ready-to-display Persian message so no component ever has to
 * translate a backend error, and raw provider errors never reach the user
 * (spec §27).
 */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly messageFa: string;

  constructor(code: ApiErrorCode, messageFa: string, cause?: unknown) {
    super(`${code}: ${messageFa}`, { cause });
    this.name = "ApiError";
    this.code = code;
    this.messageFa = messageFa;
  }
}

export function toPersianError(error: unknown): string {
  if (error instanceof ApiError) return error.messageFa;
  return "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.";
}
