import type { CampaignStatus } from "@/types/domain";

/** Statuses the wizard is allowed to resume. Finished jobs get a new draft. */
export const WIZARD_DRAFT_STATUSES: readonly CampaignStatus[] = [
  "draft",
  "brief_complete",
  "concepts_ready",
  "concept_selected",
];

export function isWizardDraft(status: CampaignStatus): boolean {
  return (WIZARD_DRAFT_STATUSES as readonly string[]).includes(status);
}
