/**
 * Domain entities.
 *
 * Field names mirror the PostgreSQL model in docs/MVP_SPEC.md §22 so that the
 * Phase 2 FastAPI responses can be consumed without reshaping anything here.
 * Identifiers stay English; only user-visible copy is Persian.
 */

export type CampaignObjective =
  | "sell_product"
  | "new_product"
  | "promotion"
  | "brand_awareness";

export type VisualStyle =
  | "luxury"
  | "minimal"
  | "friendly"
  | "bold"
  | "persian_traditional"
  | "modern";

export type CampaignStatus =
  | "draft"
  | "brief_complete"
  | "concepts_ready"
  | "concept_selected"
  | "queued"
  | "generating"
  | "ready"
  | "partial_failed"
  | "failed";

export type CopyType =
  | "caption_short"
  | "caption_friendly"
  | "caption_persuasive"
  | "story"
  | "cta"
  | "hashtags"
  | "reel_concept";

export type AssetType =
  | "uploaded_product"
  | "product_cutout"
  | "generated_background"
  | "feed_final"
  | "story_final"
  | "carousel_1"
  | "carousel_2"
  | "carousel_3";

export type BrandAssetType = "logo" | "reference_image" | "product_reference";

export interface Profile {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  locale: string;
  credit_balance_cached: number;
  free_campaigns_remaining: number;
  created_at: string;
  updated_at: string;
}

export interface Brand {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  category: string | null;
  instagram_handle: string | null;
  website: string | null;
  target_audience: string | null;
  tone: string | null;
  visual_style: VisualStyle | null;
  primary_color: string | null;
  secondary_color: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrandAsset {
  id: string;
  brand_id: string;
  asset_type: BrandAssetType;
  storage_path: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface Product {
  id: string;
  user_id: string | null;
  brand_id: string | null;
  name: string;
  description: string | null;
  price_text: string | null;
  main_benefit: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductImage {
  id: string;
  product_id: string;
  storage_path: string;
  is_primary: boolean;
  crop: CropRect;
  crop_storage_path: string | null;
  created_at: string;
}

export interface CropRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Campaign {
  id: string;
  user_id: string | null;
  anonymous_session_id: string | null;
  brand_id: string | null;
  product_id: string | null;
  objective: CampaignObjective | null;
  audience: string | null;
  visual_style: VisualStyle | null;
  selected_concept_id: string | null;
  status: CampaignStatus;
  is_free_campaign: boolean;
  created_at: string;
  updated_at: string;
}

export interface CampaignConcept {
  id: string;
  campaign_id: string;
  concept_number: number;
  title_fa: string;
  headline_fa: string;
  description_fa: string;
  /** Internal creative direction. Shown to the user as plain Persian prose. */
  visual_direction: string;
  /** Internal only. Never rendered in the customer-facing UI (spec §5.1, §23). */
  background_prompt: string;
  raw_json: Record<string, unknown>;
  selected: boolean;
  created_at: string;
}

export interface ReelConcept {
  hook_fa: string;
  scenes_fa: string[];
  cta_fa: string;
  voiceover_fa: string;
  duration_seconds: number;
}

export interface CampaignCopy {
  id: string;
  campaign_id: string;
  copy_type: CopyType;
  content: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * Everything the renderer needs to compose one ad format.
 *
 * In Phase 1 `storage_path` is null and the browser composes the asset from
 * this spec. When the backend starts producing real PNGs it will fill
 * `storage_path` and the renderer will prefer it, with no UI changes.
 */
export interface AssetRenderSpec {
  template_id: string;
  background_id: string;
  headline_fa: string;
  subheadline_fa: string | null;
  cta_fa: string | null;
  price_text: string | null;
  brand_name: string | null;
  product_image_path: string | null;
  /** Generated empty scene. CSS background_id is the fallback when this is null. */
  scene_image_path?: string | null;
  /**
   * cutout = rembg PNG; crop = seller-approved rectangle (rembg unavailable);
   * original = bundled sample. Never a silent full-screenshot fallback.
   */
  product_source?: "cutout" | "crop" | "original";
  slide_label_fa?: string | null;
  /** Set when this particular asset failed while the rest of the campaign succeeded. */
  failed?: boolean;
}

export interface CampaignAsset {
  id: string;
  campaign_id: string;
  asset_type: AssetType;
  storage_path: string | null;
  width: number;
  height: number;
  template_id: string | null;
  metadata_json: AssetRenderSpec | Record<string, unknown>;
  created_at: string;
}

/** Aggregate returned by GET /api/campaigns/{id}. */
export interface CampaignDetail {
  campaign: Campaign;
  product: Product | null;
  product_images: ProductImage[];
  concepts: CampaignConcept[];
  copies: CampaignCopy[];
  assets: CampaignAsset[];
  brand: Brand | null;
}

/** Compact shape for dashboard cards. */
export interface CampaignSummary {
  id: string;
  product_name: string | null;
  brand_name: string | null;
  status: CampaignStatus;
  /**
   * Rendered feed ad once the backend produces one, otherwise the source photo.
   * Mirrors `AdCanvas`: a real image always wins over a composed preview.
   */
  thumbnail_path: string | null;
  /**
   * Lets the dashboard show the finished ad rather than the raw upload while
   * assets are still composed in the browser. Null until a campaign is ready.
   */
  thumbnail_spec: AssetRenderSpec | null;
  created_at: string;
}

export type GenerationStage =
  | "planning"
  | "visual"
  | "captions"
  | "story"
  | "finalizing";

export interface CampaignStatusResponse {
  campaign_id: string;
  status: CampaignStatus;
  stage: GenerationStage | null;
  percent: number;
  message_fa: string | null;
  failed_asset_types: AssetType[];
}

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  locale: string;
  free_campaigns_remaining: number;
}

export interface Session {
  user: SessionUser;
  /** Mock token. Phase 2 replaces this with a Supabase access token. */
  access_token: string;
}
