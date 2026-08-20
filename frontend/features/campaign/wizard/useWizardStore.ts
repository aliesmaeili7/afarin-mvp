"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { isWizardDraft } from "./draftStatus";

/**
 * Transient wizard state only.
 *
 * The campaign itself is server state: every step writes through the API, so
 * the only thing worth persisting on the client is which draft we are editing.
 * The current step comes from the URL and each step's form buffer is local
 * component state.
 */
interface WizardState {
  campaignId: string | null;
  setCampaignId: (campaignId: string | null) => void;
  clear: () => void;
}

export const useWizardStore = create<WizardState>()(
  persist(
    (set) => ({
      campaignId: null,
      setCampaignId: (campaignId) => set({ campaignId }),
      clear: () => set({ campaignId: null }),
    }),
    { name: "afarin.wizard" },
  ),
);

export async function beginNewCampaign(brandId?: string | null): Promise<string> {
  useWizardStore.getState().clear();
  const campaign = await api.createCampaign({ brand_id: brandId ?? null });
  useWizardStore.getState().setCampaignId(campaign.id);
  track("campaign_started", { campaign_id: campaign.id });
  return campaign.id;
}

export function resumeCampaign(campaignId: string): void {
  useWizardStore.getState().setCampaignId(campaignId);
}

export async function reuseOrCreateDraft(): Promise<string> {
  const existingId = useWizardStore.getState().campaignId;
  if (existingId) {
    try {
      const detail = await api.getCampaign(existingId);
      if (isWizardDraft(detail.campaign.status)) return existingId;
    } catch {
      // Stale id, a finished campaign, or someone else's draft.
    }
  }
  return beginNewCampaign();
}

