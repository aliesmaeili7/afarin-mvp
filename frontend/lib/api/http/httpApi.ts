import type {
  Brand,
  Campaign,
  CampaignAsset,
  CampaignConcept,
  CampaignCopy,
  CampaignDetail,
  CampaignStatusResponse,
  CampaignSummary,
  Product,
  ProductImage,
  Session,
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
  type GoogleSignInInput,
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

  async requestEmailCode(input: EmailCodeRequest): Promise<void> {
    const email = input.email.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      throw new ApiError("validation_error", "ایمیل معتبر وارد کن.");
    }

    const { error } = await getSupabaseClient().auth.signInWithOtp({
      email,
      options: { shouldCreateUser: true },
    });
    if (error) throw toAuthError(error);
  },

  async verifyEmailCode(input: EmailCodeVerification): Promise<Session> {
    const code = input.code.trim();
    if (!/^\d{6}$/.test(code)) {
      throw new ApiError("validation_error", "کد ۶ رقمی رو کامل وارد کن.");
    }

    const { error } = await getSupabaseClient().auth.verifyOtp({
      email: input.email.trim().toLowerCase(),
      token: code,
      type: "email",
    });
    if (error) throw toAuthError(error);

    return httpApi.adoptAnonymousWork();
  },

  async signInWithGoogle(input: GoogleSignInInput): Promise<void> {
    const { error } = await getSupabaseClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: input.redirect_to },
    });
    // Success navigates away, so reaching here at all means it failed.
    if (error) throw toAuthError(error);
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

/**
 * Supabase reports errors in English. Sellers see Persian, and the original is
 * left on `cause` for debugging (spec §27).
 */
function toAuthError(error: { message: string; status?: number }): ApiError {
  const message = error.message.toLowerCase();

  if (message.includes("expired")) {
    return new ApiError("validation_error", "این کد منقضی شده. یه کد جدید بگیر.", error);
  }
  if (message.includes("invalid") || error.status === 403) {
    return new ApiError("validation_error", "کد واردشده درست نیست.", error);
  }
  if (message.includes("rate") || error.status === 429) {
    return new ApiError(
      "rate_limited",
      "تعداد تلاش‌ها زیاد بود. چند دقیقه دیگه دوباره امتحان کن.",
      error,
    );
  }
  return new ApiError("unknown", "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.", error);
}
