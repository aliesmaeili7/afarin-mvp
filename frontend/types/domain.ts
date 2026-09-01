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
  | "candidates_ready"
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

export type VisualCreationMode = "accurate" | "creative";

export interface VisualRecipe {
  style_id: string;
  template_id: string;
  source?: "smart" | "custom";
  title_fa?: string;
  description_fa?: string;
  warning_fa?: string;
  scene_direction?: string;
  identity_constraints?: string[];
  text_safe_area?: string;
  recommended?: { style_id: string; template_id: string };
}

export interface VisualCatalogEntry {
  id: string;
  label_fa: string;
  description_fa: string;
  preview_path: string;
  default_text_safe_area?: string;
  needs_person?: boolean;
  allows_duplicate_products?: boolean;
  person_affinity?: string;
  human_requirement?: string;
  preferred_templates?: string[];
  discouraged_templates?: string[];
  preferred_styles?: string[];
  discouraged_styles?: string[];
}

export interface VisualCatalog {
  templates: VisualCatalogEntry[];
}

export interface VisualCandidate {
  id: string;
  slot: number;
  kind: string;
  storage_path: string;
  hard_failed: boolean;
  hidden: boolean;
  created_at: string;
}

export interface VisualAttempt {
  id: string;
  attempt_number: number;
  source: string;
  status: string;
  auto_repair_used: boolean;
  selected_candidate_id: string | null;
  recipe_json: VisualRecipe;
}

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

export type BrandAssetType = "logo" | "reference_image" | "product_reference";

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
  clean_reference_storage_path?: string | null;
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
  visual_creation_mode?: VisualCreationMode | null;
  requested_image_count?: number;
  visual_instruction?: string | null;
  selected_template_id?: string | null;
  visual_recipe_json?: VisualRecipe | Record<string, unknown>;
  planner_result_json?: Record<string, unknown>;
  current_visual_attempt_id?: string | null;
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

export type TextLayerRole =
  | "headline"
  | "subheadline"
  | "cta"
  | "price"
  | "brand"
  | "slide_label"
  | "custom";

export type TextLayerAlign = "right" | "center" | "left";
export type TextLayerBackground = "none" | "pill" | "rect";
export type TextLayerWeight = 400 | 700;

/**
 * One editable Persian type overlay. Positions are normalized 0–1 against the
 * asset's own width/height so a 200px preview and a 1080px export match.
 */
export interface TextLayer {
  id: string;
  role: TextLayerRole;
  text: string;
  x: number;
  y: number;
  width: number;
  font_family: string;
  font_size: number;
  font_weight: TextLayerWeight;
  color: string;
  text_align: TextLayerAlign;
  opacity: number;
  background: TextLayerBackground;
  background_color: string | null;
  background_opacity: number;
  shadow: boolean;
}

/**
 * Everything the renderer needs to compose one ad format.
 *
 * In Phase 1 `storage_path` is null and the browser composes the asset from
 * this spec. When the backend starts producing real PNGs it will fill
 * `storage_path` and the renderer will prefer it, with no UI changes.
 *
 * `text_layers` is optional presentation. Missing/null keeps the original flex
 * template so old campaigns render unchanged.
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
  product_source?: "cutout" | "crop" | "original" | "generated";
  slide_label_fa?: string | null;
  /** Set when this particular asset failed while the rest of the campaign succeeded. */
  failed?: boolean;
  /**
   * Free-positioned type. Absent = legacy flex layout. Null after reset.
   * Each visual asset stores its own array so Feed/Story/Carousel stay independent.
   */
  text_layers?: TextLayer[] | null;
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
  visual_attempt?: VisualAttempt | null;
  visual_candidates?: VisualCandidate[];
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

export type GenerationStage = "planning" | "visual" | "finalizing";

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

/* --- Educational content ------------------------------------------------- */

export type EducationalPostStatus = "queued" | "generating" | "ready" | "failed";

export type EducationalThemeSource = "builtin" | "user";

export interface EducationalThemePalette {
  primary: string[];
  secondary: string[];
  background?: string;
  text?: string;
}

/**
 * Style memory only: palette, material, mood, lighting, motifs.
 * Never layout, fonts, CTA/badge chrome, or the lesson of the post it came from.
 */
export interface EducationalThemeSpec {
  name?: string;
  palette: EducationalThemePalette;
  illustration_style: string;
  mood?: string;
  lighting?: string;
  shape_language: string;
  decorative_motifs: string[];
  background_treatment?: string;
}

/** A built-in theme as offered to the picker. */
export interface BuiltinEducationalTheme extends EducationalThemeSpec {
  id: string;
  name: string;
  source: EducationalThemeSource;
}

/** A theme the user saved from one of their own posts. */
export interface EducationalTheme {
  id: string;
  name: string;
  source: EducationalThemeSource;
  theme_json: EducationalThemeSpec;
  created_at: string;
  updated_at: string;
}

export interface EducationalThemeList {
  builtin: BuiltinEducationalTheme[];
  saved: EducationalTheme[];
}

/**
 * The agent's stored output. `final_prompt` is present for dev tooling only and
 * is never shown to a normal user.
 */
export interface EducationalAgentResult {
  language: "fa" | "en";
  final_prompt: string;
  theme?: {
    name_suggestion: string;
    primary_colors: string[];
    secondary_colors: string[];
    illustration_style: string;
    mood: string;
    lighting: string;
    shape_language: string;
    decorative_motifs: string[];
  };
  theme_style_notes?: string | null;
  safety_notes?: string | null;
}

/** Image-only result. Advertising composition fields must not appear here. */
export interface EducationalRenderSpec {
  render_mode: "educational";
  image_path: string | null;
}

export interface EducationalPost {
  id: string;
  user_prompt: string;
  selected_theme_id: string | null;
  selected_builtin_theme_id: string | null;
  language: "fa" | "en" | null;
  headline: string | null;
  status: EducationalPostStatus;
  error_message: string | null;
  image_storage_path: string | null;
  agent_json: EducationalAgentResult | Record<string, never>;
  theme_json: EducationalThemeSpec | Record<string, never>;
  render_spec_json: EducationalRenderSpec | Record<string, never>;
  wall_time_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface EducationalPostSummary {
  id: string;
  headline: string | null;
  status: EducationalPostStatus;
  language: "fa" | "en" | null;
  image_storage_path: string | null;
  created_at: string;
}

export interface EducationalPostStatusResponse {
  post_id: string;
  status: EducationalPostStatus;
  stage: GenerationStage | null;
  percent: number;
  message_fa: string | null;
}
