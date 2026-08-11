"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { Skeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { VISUAL_STYLES } from "@/lib/content/styles";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { buildStylePreviewSpec } from "@/features/campaign/ad-renderer/previewSpec";
import type { VisualStyle } from "@/types/domain";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

/** Style-matched suggestion when the user asks us to choose (spec §5.5). */
const OBJECTIVE_STYLE_HINT: Record<string, VisualStyle> = {
  sell_product: "modern",
  new_product: "bold",
  promotion: "friendly",
  brand_awareness: "luxury",
};

export function StyleStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(4, detail, loading, campaignId);

  const [style, setStyle] = useHydratedForm<VisualStyle | null>(
    detail?.campaign.id ?? null,
    () => detail?.campaign.visual_style ?? null,
    null,
  );
  const [autoPicked, setAutoPicked] = useState(false);
  const [saving, setSaving] = useState(false);

  function handleAutoPick() {
    const objective = detail?.campaign.objective ?? "sell_product";
    setStyle(OBJECTIVE_STYLE_HINT[objective] ?? "modern");
    setAutoPicked(true);
  }

  async function handleContinue() {
    if (!detail || !style) return;
    setSaving(true);
    try {
      await api.updateCampaign(detail.campaign.id, { visual_style: style });
      track("style_selected", { style, auto: autoPicked });
      router.push("/create/concepts");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[3]}
      backHref="/create/objective"
      heading="دوست داری تبلیغت چه حسی داشته باشه؟"
      description="هر کارت، محصول خودت رو توی همون سبک نشون می‌ده."
      footer={
        <Button
          fullWidth
          size="lg"
          loading={saving}
          disabled={!style}
          onClick={handleContinue}
        >
          ادامه
        </Button>
      }
    >
      {loading || blocked ? (
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-64 w-full" />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-3">
            {VISUAL_STYLES.map((option) => (
              <ChoiceCard
                key={option.value}
                selected={style === option.value}
                onSelect={() => {
                  setStyle(option.value);
                  setAutoPicked(false);
                }}
                title={option.label_fa}
                description={option.description_fa}
                media={
                  <span className="block" aria-hidden="true">
                    <AdCanvas
                      spec={buildStylePreviewSpec(option.value, detail)}
                      width={1080}
                      height={1350}
                    />
                  </span>
                }
              />
            ))}
          </div>

          <button
            type="button"
            onClick={handleAutoPick}
            className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
          >
            خودت بهترین سبک رو انتخاب کن
          </button>

          {autoPicked && style ? (
            <p className="rounded-2xl bg-brand-50 p-4 text-sm leading-7 text-brand-800">
              با توجه به هدف تبلیغت، سبک{" "}
              <span className="font-bold">
                {VISUAL_STYLES.find((item) => item.value === style)?.label_fa}
              </span>{" "}
              رو پیشنهاد می‌کنیم. اگه دوست نداشتی، هر کدوم دیگه‌ای رو انتخاب کن.
            </p>
          ) : null}
        </div>
      )}
    </WizardShell>
  );
}
