import type {
  Brand,
  BrandAsset,
  Campaign,
  CampaignAsset,
  CampaignConcept,
  CampaignCopy,
  Product,
  ProductImage,
  Profile,
  Session,
} from "@/types/domain";

/**
 * Local stand-in for PostgreSQL.
 *
 * Tables are named after the schema in docs/MVP_SPEC.md §22 so that Phase 2 is
 * a matter of pointing the API at real endpoints, not reshaping data. The whole
 * document is persisted as one versioned JSON blob in localStorage; on a
 * version bump we discard it rather than migrate, since this is mock data.
 */

const STORAGE_KEY = "afarin.mock_db";
const SCHEMA_VERSION = 3;

export interface MockGenerationJob {
  id: string;
  campaign_id: string;
  job_type: "campaign_generation";
  status: "queued" | "processing" | "succeeded" | "failed";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface MockDbShape {
  version: number;
  anonymous_session_id: string;
  session: Session | null;
  /** True until the seeded sample campaign has been handed to an account. */
  sample_unclaimed: boolean;
  profiles: Profile[];
  brands: Brand[];
  brand_assets: BrandAsset[];
  products: Product[];
  product_images: ProductImage[];
  campaigns: Campaign[];
  campaign_concepts: CampaignConcept[];
  campaign_copy: CampaignCopy[];
  campaign_assets: CampaignAsset[];
  generation_jobs: MockGenerationJob[];
  /** How many times concepts have been requested per campaign. */
  concept_rounds: Record<string, number>;
  /** Email → password. Missing for OTP-only accounts until they set one. */
  account_passwords: Record<string, string>;
  pending_password_reset: string | null;
}

export function newId(prefix: string): string {
  const uuid =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  return `${prefix}_${uuid.replace(/-/g, "").slice(0, 16)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

function emptyDb(): MockDbShape {
  return {
    version: SCHEMA_VERSION,
    anonymous_session_id: newId("anon"),
    session: null,
    sample_unclaimed: true,
    profiles: [],
    brands: [],
    brand_assets: [],
    products: [],
    product_images: [],
    campaigns: [],
    campaign_concepts: [],
    campaign_copy: [],
    campaign_assets: [],
    generation_jobs: [],
    concept_rounds: {},
    account_passwords: {},
    pending_password_reset: null,
  };
}

/**
 * Used during SSR, where there is no localStorage. Nothing is persisted; every
 * screen that reads data does so from a client effect.
 */
let memoryDb: MockDbShape | null = null;

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

export function readDb(): MockDbShape {
  if (!isBrowser()) {
    memoryDb ??= emptyDb();
    return memoryDb;
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const seeded = seed(emptyDb());
      writeDb(seeded);
      return seeded;
    }
    const parsed = JSON.parse(raw) as MockDbShape;
    if (parsed.version !== SCHEMA_VERSION) {
      const seeded = seed(emptyDb());
      writeDb(seeded);
      return seeded;
    }
    return parsed;
  } catch {
    const seeded = seed(emptyDb());
    writeDb(seeded);
    return seeded;
  }
}

export function writeDb(db: MockDbShape): void {
  if (!isBrowser()) {
    memoryDb = db;
    return;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // Quota exceeded: the app keeps working for the current session.
  }
}

/** Read-modify-write helper so every mutation persists atomically. */
export function mutateDb<T>(mutation: (db: MockDbShape) => T): T {
  const db = readDb();
  const result = mutation(db);
  writeDb(db);
  return result;
}

export function resetDb(): void {
  if (isBrowser()) localStorage.removeItem(STORAGE_KEY);
  memoryDb = null;
}

export const SAMPLE_CAMPAIGN_ID = "cmp_sample_saffron";
export const SAMPLE_BRAND_ID = "brd_sample_sahand";
const SAMPLE_PRODUCT_ID = "prd_sample_saffron";
export const SAMPLE_IMAGE_PATH = "public://mock/product-saffron.svg";

/**
 * One finished sample campaign so a brand-new account has something to look at
 * on the dashboard. It is explicitly labelled «نمونه» so it can never be
 * mistaken for the user's own work.
 */
function seed(db: MockDbShape): MockDbShape {
  const createdAt = new Date(Date.now() - 3 * 24 * 3600 * 1000).toISOString();

  db.brands.push({
    id: SAMPLE_BRAND_ID,
    user_id: null,
    name: "سحند",
    description: "فروش زعفران و سوغات ایرانی با بسته‌بندی هدیه",
    category: "مواد غذایی",
    instagram_handle: "sahand.shop",
    website: null,
    target_audience: "کسانی که دنبال هدیه لوکس ایرانی هستن",
    tone: "لوکس و مؤدبانه",
    visual_style: "luxury",
    primary_color: "#7a2e1e",
    secondary_color: "#e9b44c",
    created_at: createdAt,
    updated_at: createdAt,
  });

  db.products.push({
    id: SAMPLE_PRODUCT_ID,
    user_id: null,
    brand_id: SAMPLE_BRAND_ID,
    name: "زعفران ممتاز (نمونه)",
    description: "زعفران یک گرمی مناسب هدیه",
    price_text: "۳۹۹ هزار تومان",
    main_benefit: "بسته‌بندی هدیه و کیفیت صادراتی",
    created_at: createdAt,
    updated_at: createdAt,
  });

  db.product_images.push({
    id: newId("img"),
    product_id: SAMPLE_PRODUCT_ID,
    storage_path: SAMPLE_IMAGE_PATH,
    is_primary: true,
    crop: { x: 0, y: 0, width: 1, height: 1 },
    crop_storage_path: null,
    created_at: createdAt,
  });

  db.campaigns.push({
    id: SAMPLE_CAMPAIGN_ID,
    user_id: null,
    anonymous_session_id: null,
    brand_id: SAMPLE_BRAND_ID,
    product_id: SAMPLE_PRODUCT_ID,
    objective: "sell_product",
    audience: "کسانی که دنبال هدیه لوکس هستن",
    visual_style: "luxury",
    selected_concept_id: null,
    status: "ready",
    is_free_campaign: true,
    created_at: createdAt,
    updated_at: createdAt,
  });

  return db;
}
