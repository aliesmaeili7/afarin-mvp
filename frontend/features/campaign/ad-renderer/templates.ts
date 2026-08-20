import type { AssetType } from "@/types/domain";

/**
 * Campaign layout templates (spec §15).
 *
 * A template describes where the product, headline, subheadline, price, CTA and
 * brand name sit. Sizes are expressed in container-query width units (`cqw`) so
 * one definition renders identically in a 200px thumbnail and in the 1080px
 * export.
 *
 * The areas are a vertical stack rather than absolute boxes on purpose: Persian
 * headlines vary a lot in length, and a stack cannot overflow or collide the
 * way fixed rectangles do.
 */
export type TemplateOrder = "product_first" | "headline_first" | "statement";

export interface AdTemplate {
  id: string;
  order: TemplateOrder;
  /** Outer padding, in cqw. */
  padding: number;
  headline_size: number;
  subheadline_size: number;
  cta_size: number;
  meta_size: number;
  /** Share of the free vertical space given to the product. */
  product_flex: number;
  show_product: boolean;
  show_cta: boolean;
  align: "center" | "start";
}

export const TEMPLATES: Record<string, AdTemplate> = {
  feed_classic: {
    id: "feed_classic",
    order: "product_first",
    padding: 7,
    headline_size: 7.6,
    subheadline_size: 4,
    cta_size: 4.2,
    meta_size: 3.4,
    product_flex: 1,
    show_product: true,
    show_cta: true,
    align: "center",
  },
  story_classic: {
    id: "story_classic",
    order: "product_first",
    padding: 8,
    headline_size: 8.2,
    subheadline_size: 4.4,
    cta_size: 4.8,
    meta_size: 3.8,
    product_flex: 1,
    show_product: true,
    show_cta: true,
    align: "center",
  },
  carousel_hook: {
    id: "carousel_hook",
    order: "headline_first",
    padding: 8,
    headline_size: 9.4,
    subheadline_size: 4.2,
    cta_size: 4,
    meta_size: 3.4,
    product_flex: 1,
    show_product: true,
    show_cta: false,
    align: "start",
  },
  carousel_benefit: {
    id: "carousel_benefit",
    order: "product_first",
    padding: 8,
    headline_size: 7,
    subheadline_size: 4,
    cta_size: 4,
    meta_size: 3.4,
    product_flex: 1.2,
    show_product: true,
    show_cta: false,
    align: "center",
  },
  carousel_cta: {
    id: "carousel_cta",
    order: "statement",
    padding: 9,
    headline_size: 10,
    subheadline_size: 4.6,
    cta_size: 4.6,
    meta_size: 3.4,
    product_flex: 0.6,
    show_product: true,
    show_cta: true,
    align: "center",
  },
};

export function getTemplate(templateId: string | null | undefined): AdTemplate {
  return (templateId && TEMPLATES[templateId]) || TEMPLATES.feed_classic;
}

export const ASSET_DIMENSIONS: Record<AssetType, { width: number; height: number }> = {
  uploaded_product: { width: 1080, height: 1080 },
  product_cutout: { width: 1080, height: 1080 },
  generated_background: { width: 1080, height: 1350 },
  feed_final: { width: 1080, height: 1350 },
  story_final: { width: 1080, height: 1920 },
  carousel_1: { width: 1080, height: 1350 },
  carousel_2: { width: 1080, height: 1350 },
  carousel_3: { width: 1080, height: 1350 },
};

export const ASSET_LABELS: Record<AssetType, string> = {
  uploaded_product: "ad.asset.uploaded_product",
  product_cutout: "ad.asset.product_cutout",
  generated_background: "ad.asset.generated_background",
  feed_final: "ad.asset.feed_final",
  story_final: "ad.asset.story_final",
  carousel_1: "ad.asset.carousel_1",
  carousel_2: "ad.asset.carousel_2",
  carousel_3: "ad.asset.carousel_3",
};
