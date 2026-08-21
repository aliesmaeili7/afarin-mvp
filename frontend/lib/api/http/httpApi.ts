import type {
  Brand,
  Campaign,
  CampaignAsset,
  CampaignConcept,
  CampaignCopy,
  CampaignDetail,
  CampaignStatusResponse,
  CampaignSummary,
  CropRect,
  Product,
  ProductImage,
  Session,
  VisualCatalog,
  VisualRecipe,
} from "@/types/domain";
import { getSupabaseClient } from "@/lib/supabase/client";
import {
  ApiError,
  type AfarinApi,
  type AssetTextPatch,
  type BrandInput,
  type CreateCampaignInput,
  type EmailCodeRequest,
  type EmailCodeVerification,
  type EmailPasswordCredentials,
  type GoogleSignInInput,
  type PasswordResetRequest,
  type UpdatePasswordInput,
  type ProductInput,
  type RewriteIntent,
  type UpdateCampaignInput,
} from "../types";
import { request } from "./request";
import { createSignedUrlBatcher } from "./signedUrlBatcher";

const PUBLIC_PREFIX = "public://";

const resolveSigned = createSignedUrlBatcher((paths) =>
  request<Record<string, string | null>>("/api/assets/resolve", {
    method: "POST",
    body: { paths },
  }),
);

/**
 * The real client. Implements exactly the same AfarinApi surface as the Phase 1
 * mock, so selecting it with NEXT_PUBLIC_API_MODE=http changes no component.
 */
export const httpApi: AfarinApi = {
  createCampaign(input: CreateCampaignInput): Promise<Campaign> {
    return request<Campaign>("/api/campaigns", {
      method: "POST",
      body: { brand_id: input.brand_id ?? null },
    });
  },

  getCampaign(campaignId: string): Promise<CampaignDetail> {
    return request<CampaignDetail>(`/api/campaigns/${campaignId}`);
  },

  updateCampaign(
    campaignId: string,
    patch: UpdateCampaignInput,
  ): Promise<Campaign> {
    return request<Campaign>(`/api/campaigns/${campaignId}`, {
      method: "PATCH",
      body: patch,
    });
  },

  listCampaigns(): Promise<CampaignSummary[]> {
    return request<CampaignSummary[]>("/api/campaigns");
  },

  saveProduct(campaignId: string, input: ProductInput): Promise<Product> {
    return request<Product>(`/api/campaigns/${campaignId}/product`, {
      method: "POST",
      body: input,
    });
  },

  uploadProductImages(
    campaignId: string,
    files: File[],
  ): Promise<ProductImage[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<ProductImage[]>(`/api/campaigns/${campaignId}/images`, {
      method: "POST",
      formData,
    });
  },

  deleteProductImage(campaignId: string, imageId: string): Promise<void> {
    return request<void>(`/api/campaigns/${campaignId}/images/${imageId}`, {
      method: "DELETE",
    });
  },

  useSampleProduct(campaignId: string): Promise<ProductImage[]> {
    return request<ProductImage[]>(`/api/campaigns/${campaignId}/images/sample`, {
      method: "POST",
    });
  },

  updateProductCrop(
    campaignId: string,
    imageId: string,
    crop: CropRect,
  ): Promise<ProductImage> {
    return request<ProductImage>(
      `/api/campaigns/${campaignId}/images/${imageId}/crop`,
      { method: "PATCH", body: crop },
    );
  },

  generateConcepts(campaignId: string): Promise<CampaignConcept[]> {
    return request<CampaignConcept[]>(
      `/api/campaigns/${campaignId}/concepts/generate`,
      { method: "POST" },
    );
  },

  selectConcept(campaignId: string, conceptId: string): Promise<Campaign> {
    return request<Campaign>(
      `/api/campaigns/${campaignId}/concepts/${conceptId}/select`,
      { method: "POST" },
    );
  },

  getVisualCatalog(): Promise<VisualCatalog> {
    return request<VisualCatalog>("/api/visual-catalog");
  },

  saveVisualRecipe(campaignId: string, recipe: VisualRecipe): Promise<Campaign> {
    return request<Campaign>(`/api/campaigns/${campaignId}/visual/recipe`, {
      method: "POST",
      body: recipe,
    });
  },

  selectVisualCandidate(
    campaignId: string,
    candidateId: string,
  ): Promise<Campaign> {
    return request<Campaign>(
      `/api/campaigns/${campaignId}/visual/candidates/${candidateId}/select`,
      { method: "POST" },
    );
  },

  regenerateVisuals(campaignId: string): Promise<CampaignStatusResponse> {
    return request<CampaignStatusResponse>(
      `/api/campaigns/${campaignId}/visual/regenerate`,
      { method: "POST" },
    );
  },

  startGeneration(campaignId: string): Promise<CampaignStatusResponse> {
    return request<CampaignStatusResponse>(
      `/api/campaigns/${campaignId}/generate`,
      { method: "POST" },
    );
  },

  getCampaignStatus(campaignId: string): Promise<CampaignStatusResponse> {
    return request<CampaignStatusResponse>(`/api/campaigns/${campaignId}/status`);
  },

  updateCopy(
    campaignId: string,
    copyId: string,
    content: string,
  ): Promise<CampaignCopy> {
    return request<CampaignCopy>(`/api/campaigns/${campaignId}/copy/${copyId}`, {
      method: "PATCH",
      body: { content },
    });
  },

  rewriteCopy(
    campaignId: string,
    copyId: string,
    intent: RewriteIntent,
  ): Promise<CampaignCopy> {
    return request<CampaignCopy>(
      `/api/campaigns/${campaignId}/copy/${copyId}/rewrite`,
      { method: "POST", body: { intent } },
    );
  },

  regenerateAsset(campaignId: string, assetId: string): Promise<CampaignAsset> {
    return request<CampaignAsset>(
      `/api/campaigns/${campaignId}/assets/${assetId}/regenerate`,
      { method: "POST" },
    );
  },

  updateAssetText(
    campaignId: string,
    assetId: string,
    patch: AssetTextPatch,
  ): Promise<CampaignAsset> {
    return request<CampaignAsset>(
      `/api/campaigns/${campaignId}/assets/${assetId}`,
      { method: "PATCH", body: patch },
    );
  },

  rewriteAssetText(
    campaignId: string,
    assetId: string,
    intent: RewriteIntent,
  ): Promise<CampaignAsset> {
    return request<CampaignAsset>(
      `/api/campaigns/${campaignId}/assets/${assetId}/rewrite`,
      { method: "POST", body: { intent } },
    );
  },

  listBrands(): Promise<Brand[]> {
    return request<Brand[]>("/api/brands");
  },

  createBrand(input: BrandInput): Promise<Brand> {
    return request<Brand>("/api/brands", { method: "POST", body: input });
  },

  async getBrand(brandId: string): Promise<Brand> {
    const brands = await request<Brand[]>("/api/brands");
    const brand = brands.find((item) => item.id === brandId);
    if (!brand) throw new ApiError("not_found", "این برند پیدا نشد.");
    return brand;
  },

  updateBrand(brandId: string, patch: BrandInput): Promise<Brand> {
    return request<Brand>(`/api/brands/${brandId}`, {
      method: "PATCH",
      body: patch,
    });
  },

  async signInWithPassword(input: EmailPasswordCredentials): Promise<Session> {
    const email = normalizeEmail(input.email);
    const password = requirePassword(input.password);

    const { error } = await getSupabaseClient().auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw toAuthError(error, "password");

    return httpApi.adoptAnonymousWork();
  },

  async signUpWithPassword(input: EmailPasswordCredentials): Promise<Session> {
    const email = normalizeEmail(input.email);
    const password = requirePassword(input.password);

    const { data, error } = await getSupabaseClient().auth.signUp({
      email,
      password,
    });
    if (error) {
      if (isAlreadyRegistered(error.message)) {
        return httpApi.signInWithPassword({ email, password });
      }
      throw toAuthError(error, "password");
    }
    if (!data.session) {
      throw new ApiError(
        "validation_error",
        "حساب ساخته شد. برای ورود همان ایمیل و رمز رو بزن.",
      );
    }

    return httpApi.adoptAnonymousWork();
  },

  async requestPasswordReset(input: PasswordResetRequest): Promise<void> {
    const email = normalizeEmail(input.email);
    const redirectTo =
      input.redirect_to ??
      (typeof window === "undefined"
        ? undefined
        : new URL("/auth/reset-password", window.location.origin).toString());

    const { error } = await getSupabaseClient().auth.resetPasswordForEmail(
      email,
      redirectTo ? { redirectTo } : undefined,
    );
    if (error) throw toAuthError(error, "recovery");
  },

  async ensurePasswordRecoverySession(): Promise<void> {
    await waitForAuthSession();
  },

  async updatePassword(input: UpdatePasswordInput): Promise<Session> {
    const password = requirePassword(input.password);
    await waitForAuthSession();

    const { error } = await getSupabaseClient().auth.updateUser({ password });
    if (error) throw toAuthError(error, "password");

    return httpApi.adoptAnonymousWork();
  },

  async requestEmailCode(input: EmailCodeRequest): Promise<void> {
    const email = normalizeEmail(input.email);

    const { error } = await getSupabaseClient().auth.signInWithOtp({
      email,
      options: { shouldCreateUser: true },
    });
    if (error) throw toAuthError(error, "otp");
  },

  async verifyEmailCode(input: EmailCodeVerification): Promise<Session> {
    const code = input.code.trim();
    if (!/^\d{6}$/.test(code)) {
      throw new ApiError("validation_error", "کد ۶ رقمی رو کامل وارد کن.");
    }

    const { error } = await getSupabaseClient().auth.verifyOtp({
      email: normalizeEmail(input.email),
      token: code,
      type: "email",
    });
    if (error) throw toAuthError(error, "otp");

    return httpApi.adoptAnonymousWork();
  },

  async signInWithGoogle(input: GoogleSignInInput): Promise<void> {
    const { error } = await getSupabaseClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: input.redirect_to },
    });
    // Success navigates away, so reaching here at all means it failed.
    if (error) throw toAuthError(error, "oauth");
  },

  adoptAnonymousWork(): Promise<Session> {
    return request<Session>("/api/session/adopt", { method: "POST" });
  },

  async signOut(): Promise<void> {
    await getSupabaseClient().auth.signOut();
  },

  async getSession(): Promise<Session | null> {
    const { data } = await getSupabaseClient().auth.getSession();
    if (!data.session) return null;
    return request<Session | null>("/api/session/me");
  },

  async resolveAssetUrl(storagePath: string | null): Promise<string | null> {
    if (!storagePath) return null;
    if (storagePath.startsWith(PUBLIC_PREFIX)) {
      return `/${storagePath.slice(PUBLIC_PREFIX.length)}`;
    }
    return resolveSigned(storagePath);
  },

  async resolveAssetUrls(
    storagePaths: string[],
  ): Promise<Record<string, string | null>> {
    const resolved: Record<string, string | null> = {};
    const needsSigning = storagePaths.filter((path) => {
      if (path.startsWith(PUBLIC_PREFIX)) {
        resolved[path] = `/${path.slice(PUBLIC_PREFIX.length)}`;
        return false;
      }
      return true;
    });

    if (needsSigning.length === 0) return resolved;

    const signed = await request<Record<string, string | null>>(
      "/api/assets/resolve",
      { method: "POST", body: { paths: needsSigning } },
    );
    return { ...resolved, ...signed };
  },
};

const MIN_PASSWORD_LENGTH = 8;

function normalizeEmail(raw: string): string {
  const email = raw.trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
  }
  return email;
}

function requirePassword(password: string): string {
  if (password.length < MIN_PASSWORD_LENGTH) {
    throw new ApiError("validation_error", "رمز باید حداقل ۸ حرف باشه.");
  }
  return password;
}

async function waitForAuthSession(): Promise<void> {
  const client = getSupabaseClient();
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const { data } = await client.auth.getSession();
    if (data.session) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new ApiError(
    "unauthorized",
    "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
  );
}

function isAlreadyRegistered(message: string): boolean {
  const lower = message.toLowerCase();
  return lower.includes("already registered") || lower.includes("already been registered");
}

/**
 * Supabase reports errors in English. Sellers see Persian, and the original is
 * left on `cause` for debugging (spec §27).
 */
function toAuthError(
  error: { message: string; status?: number },
  surface: "otp" | "password" | "oauth" | "recovery",
): ApiError {
  const message = error.message.toLowerCase();

  if (message.includes("rate") || error.status === 429) {
    return new ApiError(
      "rate_limited",
      "تعداد تلاش‌ها زیاد بود. چند دقیقه دیگه دوباره امتحان کن.",
      error,
    );
  }
  if (surface === "password") {
    if (message.includes("email not confirmed")) {
      return new ApiError(
        "validation_error",
        "این حساب هنوز فعال نشده. از ورود با کد ایمیل استفاده کن.",
        error,
      );
    }
    if (message.includes("password")) {
      return new ApiError("validation_error", "رمز باید حداقل ۸ حرف باشه.", error);
    }
    if (message.includes("invalid") || error.status === 400) {
      return new ApiError("validation_error", "ایمیل یا رمز درست نیست.", error);
    }
  }
  if (surface === "recovery") {
    if (message.includes("expired") || message.includes("invalid")) {
      return new ApiError(
        "validation_error",
        "این لینک معتبر نیست یا منقضی شده. دوباره درخواست بده.",
        error,
      );
    }
  }
  if (surface === "otp") {
    if (message.includes("expired")) {
      return new ApiError(
        "validation_error",
        "این کد منقضی شده. یه کد جدید بگیر.",
        error,
      );
    }
    if (message.includes("invalid") || error.status === 403) {
      return new ApiError("validation_error", "کد واردشده درست نیست.", error);
    }
  }
  return new ApiError("unknown", "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.", error);
}
