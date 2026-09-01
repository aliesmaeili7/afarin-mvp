import { describe, expect, it } from "vitest";
import type { CampaignDetail } from "@/types/domain";
import { furthestAllowedStep, isLegacyDirection } from "./wizardSteps";

function detail(overrides: Partial<CampaignDetail["campaign"]> = {}): CampaignDetail {
  return {
    campaign: {
      id: "c1",
      user_id: null,
      anonymous_session_id: "a1",
      brand_id: null,
      product_id: "p1",
      objective: null,
      audience: null,
      visual_style: null,
      selected_concept_id: null,
      status: "draft",
      is_free_campaign: true,
      created_at: "",
      updated_at: "",
      ...overrides,
    },
    product: {
      id: "p1",
      user_id: null,
      brand_id: null,
      name: "هودی",
      description: null,
      price_text: null,
      main_benefit: null,
      created_at: "",
      updated_at: "",
    },
    product_images: [
      {
        id: "img1",
        product_id: "p1",
        storage_path: "x",
        is_primary: true,
        crop: { x: 0, y: 0, width: 1, height: 1 },
        crop_storage_path: null,
        created_at: "",
      },
    ],
    concepts: [],
    copies: [],
    assets: [],
    brand: null,
    visual_attempt: null,
    visual_candidates: [],
  };
}

describe("furthestAllowedStep", () => {
  it("stops at the photo step until name and image exist", () => {
    expect(furthestAllowedStep(null)).toBe(1);
    const empty = detail();
    empty.product = { ...empty.product!, name: "" };
    empty.product_images = [];
    expect(furthestAllowedStep(empty)).toBe(1);
    expect(furthestAllowedStep(detail())).toBe(2);
  });

  it("opens the visual step only after objective and mood", () => {
    expect(
      furthestAllowedStep(
        detail({ objective: "sell_product", visual_style: "luxury" }),
      ),
    ).toBe(3);
  });
});

describe("isLegacyDirection", () => {
  it("treats missing style_id as a pre-Director concept row", () => {
    expect(isLegacyDirection(undefined)).toBe(true);
    expect(isLegacyDirection({ background_id: "modern_ice" })).toBe(true);
    expect(isLegacyDirection({ style_id: "anime" })).toBe(false);
  });
});
