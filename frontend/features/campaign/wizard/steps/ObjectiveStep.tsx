"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
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
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import type { CampaignObjective } from "@/types/domain";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

export function ObjectiveStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
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
      toast(t("wizard.pickObjectiveFirst"), "info");
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
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[2]}
      backHref="/create/product"
      heading={t("wizard.objectiveTitle")}
      description={t("wizard.objectiveDescription")}
      footer={
        <Button
          fullWidth
          size="lg"
          loading={saving}
          disabled={!objective}
          onClick={handleContinue}
        >
          {t("common.continue")}
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
                    {t(`campaign.objective.${option.value}.label` as TranslationKey)}
                  </span>
                }
                description={t(
                  `campaign.objective.${option.value}.description` as TranslationKey,
                )}
              />
            ))}
          </div>

          <section className="flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-bold text-foreground">
                {t("wizard.audienceTitle")}
              </h2>
              <p className="mt-1 text-sm leading-7 text-muted">
                {t("wizard.audienceHint")}
              </p>
            </div>

            <TextField
              label={t("wizard.audienceLabel")}
              optional
              placeholder={t("wizard.audiencePlaceholder")}
              value={audience}
              onChange={(event) => setAudience(event.target.value)}
            />

            <SuggestionChips
              items={AUDIENCE_SUGGESTIONS.map((item) => ({
                value: item.value_fa,
                label: t(`campaign.audience.${item.id}` as TranslationKey),
              }))}
              activeItem={audience}
              onSelect={setAudience}
            />

            <button
              type="button"
              onClick={handleSuggestAudience}
              className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              {t("wizard.audienceSuggest")}
            </button>
          </section>
        </div>
      )}
    </WizardShell>
  );
}
