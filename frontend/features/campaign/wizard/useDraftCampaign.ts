"use client";

import { useCallback, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { CampaignDetail } from "@/types/domain";
import { track } from "@/lib/analytics/track";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useWizardStore } from "./useWizardStore";

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
    () => (campaignId ? api.getCampaign(campaignId) : Promise.resolve(null)),
    [campaignId],
  );

  // A stale id (cleared storage, a different browser) should not trap the user
  // on a broken step.
  useEffect(() => {
    if (error && campaignId) setCampaignId(null);
  }, [error, campaignId, setCampaignId]);

  const ensureCampaign = useCallback(async () => {
    if (campaignId) return campaignId;
    creatingRef.current ??= (async () => {
      const campaign = await api.createCampaign({});
      setCampaignId(campaign.id);
      track("campaign_started", { campaign_id: campaign.id });
      return campaign.id;
    })();
    try {
      return await creatingRef.current;
    } finally {
      creatingRef.current = null;
    }
  }, [campaignId, setCampaignId]);

  return {
    detail: data ?? null,
    campaignId,
    loading,
    error,
    reload,
    ensureCampaign,
  };
}
