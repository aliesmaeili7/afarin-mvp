import { describe, expect, it } from "vitest";
import type { ProductImage } from "@/types/domain";
import { productImagePath } from "./productImagePath";

const base: ProductImage = {
  id: "i1",
  product_id: "p1",
  storage_path: "supabase://product-images/campaigns/c/products/i1.jpg",
  is_primary: true,
  crop: { x: 0.1, y: 0.2, width: 0.5, height: 0.4 },
  crop_storage_path: null,
  created_at: "2026-01-01T00:00:00.000Z",
};

describe("productImagePath", () => {
  it("prefers the crop derivative over the original upload", () => {
    expect(
      productImagePath({
        ...base,
        crop_storage_path: "supabase://product-images/campaigns/c/crops/i1.jpg",
      }),
    ).toBe("supabase://product-images/campaigns/c/crops/i1.jpg");
  });

  it("falls back to the original when there is no crop file", () => {
    expect(productImagePath(base)).toBe(base.storage_path);
  });
});
