"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { Skeleton } from "@/components/ui/Feedback";
import { SuggestionChips, TextField } from "@/components/ui/Field";
import { useToast } from "@/components/ui/Toast";
import {
  AUDIENCE_SUGGESTIONS,
  OBJECTIVES,
  SUGGESTED_AUDIENCE,
} from "@/lib/content/objectives";
import { normalizePersian } from "@/lib/format/persian";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import type { CampaignObjective } from "@/types/domain";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

export function ObjectiveStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(3, detail, loading, campaignId);

  const [brief, setBrief] = useHydratedForm<{
    objective: CampaignObjective | null;
    audience: string;
  }>(
    detail?.campaign.id ?? null,
    () => ({
      objective: detail?.campaign.objective ?? null,
      audience: detail?.campaign.audience ?? "",
    }),
    { objective: null, audience: "" },
  );
  const [saving, setSaving] = useState(false);

  const { objective, audience } = brief;
  const setObjective = (value: CampaignObjective) =>
    setBrief((current) => ({ ...current, objective: value }));
  const setAudience = (value: string) =>
    setBrief((current) => ({ ...current, audience: value }));

  function handleSuggestAudience() {
    if (!objective) {
      toast("اول هدف تبلیغ رو انتخاب کن.", "info");
      return;
    }
    setAudience(SUGGESTED_AUDIENCE[objective]);
  }

  async function handleContinue() {
    if (!detail || !objective) return;
    setSaving(true);
    try {
      await api.updateCampaign(detail.campaign.id, {
        objective,
        audience: normalizePersian(audience).trim() || null,
      });
      router.push("/create/style");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[2]}
      backHref="/create/product"
      heading="از این تبلیغ چه نتیجه‌ای می‌خوای؟"
      description="یکی رو انتخاب کن تا لحن و پیام تبلیغ رو متناسبش بنویسیم."
      footer={
        <Button
          fullWidth
          size="lg"
          loading={saving}
          disabled={!objective}
          onClick={handleContinue}
        >
          ادامه
        </Button>
      }
    >
      {loading || blocked ? (
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Two columns even on the narrowest phone, so the audience question
              below stays visible without scrolling. */}
          <div className="grid grid-cols-2 gap-3">
            {OBJECTIVES.map((option) => (
              <ChoiceCard
                key={option.value}
                selected={objective === option.value}
                onSelect={() => setObjective(option.value)}
                title={
                  <span className="flex flex-col gap-1">
                    <span className="text-lg leading-none" aria-hidden="true">
                      {option.emoji}
                    </span>
                    {option.label_fa}
                  </span>
                }
                description={option.description_fa}
              />
            ))}
          </div>

          <section className="flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-bold text-ink-900">
                این محصول بیشتر برای چه کسیه؟
              </h2>
              <p className="mt-1 text-sm leading-7 text-ink-500">
                لازم نیست دقیق باشه؛ یکی از پیشنهادها رو بزن یا خودت بنویس.
              </p>
            </div>

            <TextField
              label="مخاطب هدف"
              optional
              placeholder="مثلاً خانم‌های ۲۰ تا ۳۵ سال"
              value={audience}
              onChange={(event) => setAudience(event.target.value)}
            />

            <SuggestionChips
              items={AUDIENCE_SUGGESTIONS}
              activeItem={audience}
              onSelect={setAudience}
            />

            <button
              type="button"
              onClick={handleSuggestAudience}
              className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              مطمئن نیستم — خودت پیشنهاد بده
            </button>
          </section>
        </div>
      )}
    </WizardShell>
  );
}
