"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

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
