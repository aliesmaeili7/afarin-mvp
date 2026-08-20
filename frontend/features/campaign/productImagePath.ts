import type { ProductImage } from "@/types/domain";

/** The pixels that should appear in ads: crop first, never the raw screenshot. */
export function productImagePath(image: ProductImage | null | undefined): string | null {
  if (!image) return null;
  return image.crop_storage_path || image.storage_path;
}
