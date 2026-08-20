"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { Container } from "@/components/layout/Container";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import type { CampaignDetail } from "@/types/domain";
import { beginNewCampaign, resumeCampaign } from "@/features/campaign/wizard/useWizardStore";
import { AssetExportProvider } from "./ad-renderer/AssetExportProvider";
import { GenerationProgress } from "./generation/GenerationProgress";
import { CampaignResult } from "./result/CampaignResult";

/**
 * `/campaigns/{id}` renders progress or results depending on campaign status,
 * which is what makes a refresh mid-generation land in the right place.
 */
export function CampaignView({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const { toast } = useToast();
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
      toast(toPersianError(caught), "error");
    } finally {
      setRetrying(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="min-h-dvh bg-ink-50">
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
      <div className="min-h-dvh bg-ink-50">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <ErrorState
            title="این کمپین پیدا نشد"
            description="ممکنه لینک اشتباه باشه یا کمپین روی دستگاه دیگه‌ای ساخته شده باشه."
            action={
              <Button
                onClick={() => {
                  void beginNewCampaign()
                    .then(() => router.push("/create"))
                    .catch((caught: unknown) => toast(toPersianError(caught), "error"));
                }}
              >
                ساخت کمپین جدید
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
      <div className="min-h-dvh bg-ink-50">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <ErrorState
            title="ساخت کمپین ناتموم موند"
            description="مشکل از سمت ما بود و چیزی از اطلاعاتت پاک نشده. یک بار دیگه امتحان کن."
            action={
              <Button loading={retrying} onClick={handleRetry}>
                دوباره بساز
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  if (status !== "ready" && status !== "partial_failed") {
    return (
      <div className="min-h-dvh bg-ink-50">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <EmptyState
            title="این کمپین هنوز کامل نشده"
            description="چند قدم تا آماده شدن کمپینت مونده."
            action={
              <Button
                onClick={() => {
                  resumeCampaign(campaignId);
                  router.push("/create");
                }}
              >
                ادامه ساخت کمپین
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
