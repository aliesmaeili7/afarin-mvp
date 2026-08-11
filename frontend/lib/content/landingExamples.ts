import type { AssetRenderSpec } from "@/types/domain";

export interface LandingExample {
  id: string;
  category_fa: string;
  /** The "before" photo, shown as-is. */
  product_image_path: string;
  spec: AssetRenderSpec;
}

/**
 * Landing-page demonstrations.
 *
 * The "after" side is rendered by the real AdCanvas from these specs, so the
 * homepage always shows exactly what the product actually produces.
 */
export const HERO_EXAMPLE: LandingExample = {
  id: "saffron",
  category_fa: "مواد غذایی",
  product_image_path: "public://mock/product-saffron.svg",
  spec: {
    template_id: "feed_classic",
    background_id: "luxury_night",
    headline_fa: "هدیه‌ای با عطر ایران",
    subheadline_fa: "زعفران ممتاز برای یک هدیه متفاوت",
    cta_fa: "همین حالا سفارش بده",
    price_text: "۳۹۹ هزار تومان",
    brand_name: "سحند",
    product_image_path: "public://mock/product-saffron.svg",
  },
};

export const CATEGORY_EXAMPLES: readonly LandingExample[] = [
  {
    id: "perfume",
    category_fa: "عطر و آرایشی",
    product_image_path: "public://mock/product-perfume.svg",
    spec: {
      template_id: "feed_classic",
      background_id: "luxury_velvet",
      headline_fa: "بویی که یادش می‌مونه",
      subheadline_fa: "ماندگاری بالا، مناسب هدیه",
      cta_fa: "سفارش بده",
      price_text: "۸۹۰ هزار تومان",
      brand_name: "آوا",
      product_image_path: "public://mock/product-perfume.svg",
    },
  },
  {
    id: "clothing",
    category_fa: "پوشاک",
    product_image_path: "public://mock/product-shirt.svg",
    spec: {
      template_id: "feed_classic",
      background_id: "minimal_sand",
      headline_fa: "سادگی، همیشه شیک",
      subheadline_fa: "پیراهن نخی، مناسب همه فصل‌ها",
      cta_fa: "سایزت رو انتخاب کن",
      price_text: "۴۹۹ هزار تومان",
      brand_name: "مانا",
      product_image_path: "public://mock/product-shirt.svg",
    },
  },
  {
    id: "coffee",
    category_fa: "بسته‌بندی و خوراکی",
    product_image_path: "public://mock/product-coffee.svg",
    spec: {
      template_id: "feed_classic",
      background_id: "modern_slate",
      headline_fa: "صبحت رو جدی بگیر",
      subheadline_fa: "قهوه تازه‌آسیاب، هر هفته دم در",
      cta_fa: "اشتراک بگیر",
      price_text: "۲۵۰ هزار تومان",
      brand_name: "کافه نار",
      product_image_path: "public://mock/product-coffee.svg",
    },
  },
];
