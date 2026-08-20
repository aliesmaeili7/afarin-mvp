"use client";

import { useCallback, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { CampaignDetail } from "@/types/domain";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { isWizardDraft } from "./draftStatus";
import { reuseOrCreateDraft, useWizardStore } from "./useWizardStore";

interface DraftCampaignState {
  detail: CampaignDetail | null;
  campaignId: string | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  /** Creates the draft on first real interaction, not on page view. */
  ensureCampaign: () => Promise<string>;
}

export function useDraftCampaign(): DraftCampaignState {
  const campaignId = useWizardStore((state) => state.campaignId);
  const setCampaignId = useWizardStore((state) => state.setCampaignId);
  const creatingRef = useRef<Promise<string> | null>(null);

  const { data, loading, error, reload } = useAsyncData<CampaignDetail | null>(
    async () => {
      if (!campaignId) return null;
      const detail = await api.getCampaign(campaignId);
      if (!isWizardDraft(detail.campaign.status)) {
        setCampaignId(null);
        return null;
      }
      return detail;
    },
    [campaignId],
  );

  // A stale id (cleared storage, a different browser) should not trap the user
  // on a broken step.
  useEffect(() => {
    if (error && campaignId) setCampaignId(null);
  }, [error, campaignId, setCampaignId]);

  const ensureCampaign = useCallback(async () => {
    creatingRef.current ??= reuseOrCreateDraft();
    try {
      return await creatingRef.current;
    } finally {
      creatingRef.current = null;
    }
  }, []);

  return {
    detail: data ?? null,
    campaignId: data?.campaign.id ?? null,
    loading,
    error,
    reload,
    ensureCampaign,
  };
}
