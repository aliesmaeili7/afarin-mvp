"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
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
import { VISUAL_STYLES } from "@/lib/content/styles";
import { normalizePersian } from "@/lib/format/persian";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import type { CampaignObjective, VisualStyle } from "@/types/domain";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

const OBJECTIVE_STYLE_HINT: Record<string, VisualStyle> = {
  sell_product: "modern",
  new_product: "bold",
  promotion: "friendly",
  brand_awareness: "luxury",
};

export function BriefStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(2, detail, loading, campaignId);

  const [brief, setBrief] = useHydratedForm<{
    objective: CampaignObjective | null;
    audience: string;
    style: VisualStyle | null;
  }>(
    detail?.campaign.id ?? null,
    () => ({
      objective: detail?.campaign.objective ?? null,
      audience: detail?.campaign.audience ?? "",
      style: detail?.campaign.visual_style ?? null,
    }),
    { objective: null, audience: "", style: null },
  );
  const [saving, setSaving] = useState(false);

  const { objective, audience, style } = brief;
  const ready = Boolean(objective && style);

  async function handleContinue() {
    if (!detail || !objective || !style) return;
    setSaving(true);
    try {
      await api.updateCampaign(detail.campaign.id, {
        objective,
        audience: normalizePersian(audience).trim() || null,
        visual_style: style,
      });
      track("style_selected", { style });
      router.push("/create/visual");
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  function handleSuggestAudience() {
    if (!objective) {
      toast(t("wizard.pickObjectiveFirst"), "info");
      return;
    }
    setBrief((current) => ({
      ...current,
      audience: SUGGESTED_AUDIENCE[objective],
    }));
  }

  function handleAutoStyle() {
    const next = OBJECTIVE_STYLE_HINT[objective ?? "sell_product"] ?? "modern";
    setBrief((current) => ({ ...current, style: next }));
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[1]}
      backHref="/create"
      heading={t("wizard.briefTitle")}
      description={t("wizard.briefDescription")}
      footer={
        <Button
          fullWidth
          size="lg"
          loading={saving}
          disabled={!ready}
          onClick={() => void handleContinue()}
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
                onSelect={() =>
                  setBrief((current) => ({ ...current, objective: option.value }))
                }
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
              onChange={(event) =>
                setBrief((current) => ({
                  ...current,
                  audience: event.target.value,
                }))
              }
            />
            <SuggestionChips
              items={AUDIENCE_SUGGESTIONS.map((item) => ({
                value: item.value_fa,
                label: t(`campaign.audience.${item.id}` as TranslationKey),
              }))}
              activeItem={audience}
              onSelect={(value) =>
                setBrief((current) => ({ ...current, audience: value }))
              }
            />
            <button
              type="button"
              onClick={handleSuggestAudience}
              className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              {t("wizard.audienceSuggest")}
            </button>
          </section>

          <section className="flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-bold text-foreground">
                {t("wizard.moodTitle")}
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {VISUAL_STYLES.map((option) => (
                <ChoiceCard
                  key={option.value}
                  selected={style === option.value}
                  onSelect={() =>
                    setBrief((current) => ({ ...current, style: option.value }))
                  }
                  title={t(`campaign.style.${option.value}.label` as TranslationKey)}
                  description={t(
                    `campaign.style.${option.value}.description` as TranslationKey,
                  )}
                  media={
                    <span
                      className="block h-14 w-full"
                      style={{ background: option.preview_css }}
                    />
                  }
                />
              ))}
            </div>
            <button
              type="button"
              onClick={handleAutoStyle}
              className="-mx-2 flex h-11 items-center self-start rounded-xl px-2 text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              {t("wizard.styleAuto")}
            </button>
          </section>
        </div>
      )}
    </WizardShell>
  );
}
