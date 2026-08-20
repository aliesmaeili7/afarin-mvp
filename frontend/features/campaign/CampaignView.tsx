"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { Container } from "@/components/layout/Container";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { CampaignDetail } from "@/types/domain";
import { beginNewCampaign, resumeCampaign } from "@/features/campaign/wizard/useWizardStore";
import { AssetExportProvider } from "./ad-renderer/AssetExportProvider";
import { GenerationProgress } from "./generation/GenerationProgress";
import { CampaignResult } from "./result/CampaignResult";
import { CandidatePicker } from "./result/CandidatePicker";

/**
 * `/campaigns/{id}` renders progress or results depending on campaign status,
 * which is what makes a refresh mid-generation land in the right place.
 */
export function CampaignView({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { data, loading, error, reload } = useAsyncData<CampaignDetail>(
    () => api.getCampaign(campaignId),
    [campaignId],
  );
  const [retrying, setRetrying] = useState(false);

  const handleFinished = useCallback(() => {
    void reload();
  }, [reload]);

  async function handleRetry() {
    setRetrying(true);
    try {
      await api.startGeneration(campaignId);
      await reload();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setRetrying(false);
    }
  }

  async function handleRetryVisuals() {
    setRetrying(true);
    try {
      await api.regenerateVisuals(campaignId);
      await reload();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setRetrying(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="md" className="flex flex-col gap-4 py-8">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-40 w-full" />
        </Container>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("errors.campaignNotFound")}
            description={t("errors.campaignNotFoundDescription")}
            action={
              <Button
                onClick={() => {
                  void beginNewCampaign()
                    .then(() => router.push("/create"))
                    .catch((caught: unknown) => toast(displayError(caught), "error"));
                }}
              >
                {t("result.newCampaign")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  const status = data.campaign.status;

  if (status === "queued" || status === "generating") {
    return (
      <GenerationProgress campaignId={campaignId} onFinished={handleFinished} />
    );
  }

  if (status === "failed") {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("result.failedTitle")}
            description={t("result.failedDescription")}
            action={
              <Button loading={retrying} onClick={handleRetry}>
                {t("result.retryBuild")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  if (status === "candidates_ready") {
    return <CandidatePicker detail={data} onChanged={handleFinished} />;
  }

  if (
    status === "partial_failed" &&
    data.campaign.visual_creation_mode === "creative"
  ) {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("result.visualsFailedTitle")}
            description={t("result.visualsFailedDescription")}
            action={
              <Button loading={retrying} onClick={() => void handleRetryVisuals()}>
                {t("result.retryVisuals")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  if (status !== "ready" && status !== "partial_failed") {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <EmptyState
            title={t("result.incompleteTitle")}
            description={t("result.incompleteDescription")}
            action={
              <Button
                onClick={() => {
                  resumeCampaign(campaignId);
                  router.push("/create");
                }}
              >
                {t("result.continueBuild")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  return (
    <AssetExportProvider>
      <CampaignResult detail={data} onChanged={handleFinished} />
    </AssetExportProvider>
  );
}
