import type { CampaignDetail } from "@/types/domain";
import type { TranslationKey } from "@/lib/i18n/t";

export interface WizardStep {
  index: number;
  path: string;
  titleKey: TranslationKey;
}

/** Spec §7 plus Phase 4B visual mode/recipe. */
export const WIZARD_STEPS: readonly WizardStep[] = [
  { index: 1, path: "/create", titleKey: "wizard.photo" },
  { index: 2, path: "/create/product", titleKey: "wizard.product" },
  { index: 3, path: "/create/objective", titleKey: "wizard.objective" },
  { index: 4, path: "/create/style", titleKey: "wizard.style" },
  { index: 5, path: "/create/concepts", titleKey: "wizard.concepts" },
  { index: 6, path: "/create/visual", titleKey: "wizard.visual" },
];

export const WIZARD_TOTAL = WIZARD_STEPS.length;

export function furthestAllowedStep(detail: CampaignDetail | null): number {
  if (!detail) return 1;

  const hasImage = detail.product_images.length > 0;
  if (!hasImage) return 1;

  const hasName = Boolean(detail.product?.name?.trim());
  if (!hasName) return 2;

  if (!detail.campaign.objective) return 3;
  if (!detail.campaign.visual_style) return 4;
  if (!detail.campaign.selected_concept_id) return 5;

  return 6;
}

export function stepByPath(path: string): WizardStep {
  return WIZARD_STEPS.find((step) => step.path === path) ?? WIZARD_STEPS[0];
}
