import type { CampaignDetail } from "@/types/domain";
import type { TranslationKey } from "@/lib/i18n/t";

export interface WizardStep {
  index: number;
  path: string;
  titleKey: TranslationKey;
}

export const WIZARD_STEPS: readonly WizardStep[] = [
  { index: 1, path: "/create", titleKey: "wizard.photo" },
  { index: 2, path: "/create/brief", titleKey: "wizard.brief" },
  { index: 3, path: "/create/visual", titleKey: "wizard.visual" },
];

export const WIZARD_TOTAL = WIZARD_STEPS.length;

export function furthestAllowedStep(detail: CampaignDetail | null): number {
  if (!detail) return 1;

  const hasImage = detail.product_images.length > 0;
  if (!hasImage) return 1;

  const hasName = Boolean(detail.product?.name?.trim());
  if (!hasName) return 1;

  if (!detail.campaign.objective || !detail.campaign.visual_style) return 2;

  return 3;
}

export function stepByPath(path: string): WizardStep {
  return WIZARD_STEPS.find((step) => step.path === path) ?? WIZARD_STEPS[0];
}

export function isLegacyDirection(raw: Record<string, unknown> | undefined): boolean {
  return !raw?.style_id;
}
