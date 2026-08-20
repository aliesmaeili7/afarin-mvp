import { backgroundsForStyle } from "@/lib/content/backgrounds";
import type { AssetRenderSpec, CampaignDetail, VisualStyle } from "@/types/domain";
import { productImagePath } from "@/features/campaign/productImagePath";

/**
 * Builds a render spec so the style step can preview a visual style using the
 * seller's own product rather than an abstract colour swatch. It reuses the
 * real `AdCanvas` pipeline, so what the user picks here is what they get.
 */
export function buildStylePreviewSpec(
  style: VisualStyle,
  detail: CampaignDetail | null,
): AssetRenderSpec {
  const background = backgroundsForStyle(style)[0];
  const product = detail?.product ?? null;
  const primaryImage =
    detail?.product_images.find((image) => image.is_primary) ??
    detail?.product_images[0] ??
    null;

  const name = product?.name?.trim();

  return {
    template_id: "feed_classic",
    background_id: background.id,
    headline_fa: name || "محصول تو",
    subheadline_fa: null,
    cta_fa: null,
    price_text: product?.price_text ?? null,
    brand_name: null,
    product_image_path: productImagePath(primaryImage),
  };
}
