import type { CampaignDetail } from "@/types/domain";

export interface WizardStep {
  index: number;
  path: string;
  title_fa: string;
}

/** Spec §7 — five guided steps, one decision at a time. */
export const WIZARD_STEPS: readonly WizardStep[] = [
  { index: 1, path: "/create", title_fa: "عکس محصول" },
  { index: 2, path: "/create/product", title_fa: "درباره محصول" },
  { index: 3, path: "/create/objective", title_fa: "هدف تبلیغ" },
  { index: 4, path: "/create/style", title_fa: "حس تبلیغ" },
  { index: 5, path: "/create/concepts", title_fa: "ایده‌های تبلیغ" },
];

export const WIZARD_TOTAL = WIZARD_STEPS.length;

/**
 * How far the user is allowed to jump. Deep-linking past an incomplete step
 * sends them back to the first thing that is actually missing.
 */
export function furthestAllowedStep(detail: CampaignDetail | null): number {
  if (!detail) return 1;

  const hasImage = detail.product_images.length > 0;
  if (!hasImage) return 1;

  const hasName = Boolean(detail.product?.name?.trim());
  if (!hasName) return 2;

  if (!detail.campaign.objective) return 3;
  if (!detail.campaign.visual_style) return 4;

  return 5;
}

export function stepByPath(path: string): WizardStep {
  return WIZARD_STEPS.find((step) => step.path === path) ?? WIZARD_STEPS[0];
}
