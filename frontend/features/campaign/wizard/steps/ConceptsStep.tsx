"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RefreshIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { toPersianDigits } from "@/lib/format/persian";
import type { AssetRenderSpec, CampaignConcept } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { productImagePath } from "@/features/campaign/productImagePath";
import { useSessionStore } from "@/features/auth/sessionStore";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

export function ConceptsStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, campaignId, loading, reload } = useDraftCampaign();
  const blocked = useWizardGuard(5, detail, loading, campaignId);

  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);

  const [generating, setGenerating] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestedRef = useRef(false);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  const concepts = detail?.concepts ?? [];
  const primary =
    detail?.product_images.find((image) => image.is_primary) ??
    detail?.product_images[0] ??
    null;
  const primaryImage = productImagePath(primary);

  const briefKey = [
    campaignId,
    detail?.product?.name,
    detail?.product?.description,
    detail?.product?.price_text,
    detail?.product?.main_benefit,
    detail?.campaign.objective,
    detail?.campaign.audience,
    detail?.campaign.visual_style,
  ].join("|");

  const runGenerate = useCallback(async () => {
    if (!campaignId) return;
    try {
      await api.generateConcepts(campaignId);
      await reload();
      track("concepts_generated");
    } catch (caught) {
      setError(toPersianError(caught));
    }
  }, [campaignId, reload]);

  useEffect(() => {
    requestedRef.current = false;
  }, [briefKey]);

  // The first visit generates automatically; the button below regenerates.
  const needsConcepts = !loading && !blocked && !error && concepts.length === 0;

  useEffect(() => {
    if (!needsConcepts || requestedRef.current) return;
    requestedRef.current = true;
    void runGenerate();
  }, [needsConcepts, runGenerate]);

  async function handleRegenerate() {
    setGenerating(true);
    setError(null);
    await runGenerate();
    setGenerating(false);
  }

  async function handleSelect(concept: CampaignConcept) {
    if (!campaignId) return;
    setSelecting(concept.id);
    try {
      await api.selectConcept(campaignId, concept.id);
      track("concept_selected", { concept_number: concept.concept_number });

      if (!useSessionStore.getState().loaded) {
        await useSessionStore.getState().load();
      }
      if (useSessionStore.getState().session) {
        await api.startGeneration(campaignId);
        track("generation_started", { campaign_id: campaignId });
        router.push(`/campaigns/${campaignId}`);
        return;
      }
      router.push("/create/signup");
    } catch (caught) {
      toast(toPersianError(caught), "error");
      setSelecting(null);
    }
  }

  const busy = loading || blocked || generating || needsConcepts;

  return (
    <WizardShell
      step={WIZARD_STEPS[4]}
      backHref="/create/style"
      heading={busy ? "داریم سه ایده برات می‌سازیم" : "سه ایده برای تبلیغت آماده کردیم"}
      description={
        busy
          ? "چند لحظه صبر کن."
          : "یکی رو انتخاب کن تا کمپین کاملت رو بسازیم."
      }
      footer={
        <Button
          fullWidth
          size="lg"
          variant="outline"
          loading={generating}
          disabled={busy}
          onClick={handleRegenerate}
          iconStart={<RefreshIcon width={18} height={18} />}
        >
          سه ایده جدید بده
        </Button>
      }
    >
      {error ? (
        <ErrorState
          description={error}
          action={
            <Button variant="outline" onClick={handleRegenerate}>
              دوباره امتحان کن
            </Button>
          }
        />
      ) : busy ? (
        <ConceptsLoading />
      ) : (
        <div className="flex flex-col gap-4">
          {concepts.map((concept) => {
            const spec: AssetRenderSpec = {
              template_id: "feed_classic",
              background_id:
                typeof concept.raw_json?.background_id === "string"
                  ? concept.raw_json.background_id
                  : "modern_ice",
              headline_fa: concept.headline_fa,
              subheadline_fa: null,
              cta_fa: null,
              price_text: null,
              brand_name: null,
              product_image_path: primaryImage,
            };

            return (
              <Card key={concept.id} className="overflow-hidden">
                <div className="relative">
                  <AdCanvas spec={spec} width={1080} height={1350} />
                  <span className="absolute top-3 start-3 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-ink-800 shadow-soft">
                    ایده {toPersianDigits(concept.concept_number)}
                  </span>
                </div>

                <div className="flex flex-col gap-2 p-4">
                  <h3 className="text-base font-bold text-ink-900">
                    {concept.title_fa}
                  </h3>
                  <p className="text-sm leading-7 text-ink-500">
                    {concept.description_fa}
                  </p>
                  <Button
                    fullWidth
                    className="mt-2"
                    loading={selecting === concept.id}
                    disabled={selecting !== null && selecting !== concept.id}
                    onClick={() => handleSelect(concept)}
                    iconStart={<SparkleIcon width={18} height={18} />}
                  >
                    این رو انتخاب کن
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </WizardShell>
  );
}

function ConceptsLoading() {
  return (
    <div className="flex flex-col gap-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-brand-700">
        <span className="size-4 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        در حال آماده کردن ایده‌های تبلیغ…
      </p>
      {Array.from({ length: 3 }, (_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-3xl border border-ink-100 bg-white"
        >
          <Skeleton className="aspect-4/5 w-full rounded-none" />
          <div className="flex flex-col gap-2 p-4">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        </div>
      ))}
    </div>
  );
}
