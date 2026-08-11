import type { CampaignObjective, VisualStyle } from "@/types/domain";

/**
 * Everything the fixtures need to produce copy that actually mentions the
 * user's product. Assembled by the mock API from the campaign brief so that
 * different answers visibly produce different Persian output.
 */
export interface CopyContext {
  productName: string;
  description: string | null;
  priceText: string | null;
  benefit: string | null;
  brandName: string | null;
  audience: string | null;
  objective: CampaignObjective;
  style: VisualStyle;
  /** Increments each time the user asks for fresh output. */
  round: number;
}

export function pick<T>(items: readonly T[], index: number): T {
  return items[((index % items.length) + items.length) % items.length];
}

/** Rotates a list so repeat requests return a different order. */
export function rotate<T>(items: readonly T[], offset: number): T[] {
  if (items.length === 0) return [];
  const shift = ((offset % items.length) + items.length) % items.length;
  return [...items.slice(shift), ...items.slice(0, shift)];
}
