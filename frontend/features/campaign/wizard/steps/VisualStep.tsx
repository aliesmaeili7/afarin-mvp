"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { useSessionStore } from "@/features/auth/sessionStore";
import { Button } from "@/components/ui/Button";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { Skeleton } from "@/components/ui/Feedback";
import { TextAreaField } from "@/components/ui/Field";
import { useToast } from "@/components/ui/Toast";
import { catalogDescription, catalogLabel } from "@/lib/i18n/catalog";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { VisualCatalogEntry } from "@/types/domain";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

export function VisualStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t, locale } = useI18n();
  const displayError = useDisplayError();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(3, detail, loading, campaignId);
  const [templates, setTemplates] = useState<VisualCatalogEntry[] | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(
    detail?.campaign.selected_template_id ?? null,
  );
  const [instruction, setInstruction] = useState(
    detail?.campaign.visual_instruction ?? "",
  );
  const [count, setCount] = useState<1 | 3>(
    detail?.campaign.requested_image_count === 3 ? 3 : 1,
  );
  const [saving, setSaving] = useState(false);

  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    void api.getVisualCatalog().then((catalog) => {
      setTemplates(catalog.templates);
    });
  }, []);

  useEffect(() => {
    setTemplateId(detail?.campaign.selected_template_id ?? null);
    setInstruction(detail?.campaign.visual_instruction ?? "");
    setCount(detail?.campaign.requested_image_count === 3 ? 3 : 1);
  }, [
    detail?.campaign.selected_template_id,
    detail?.campaign.visual_instruction,
    detail?.campaign.requested_image_count,
  ]);

  if (blocked) return null;

  async function handleGenerate() {
    if (!detail) return;
    setSaving(true);
    try {
      await api.updateCampaign(detail.campaign.id, {
        selected_template_id: templateId,
        visual_instruction: instruction.trim() || null,
        requested_image_count: count,
      });
      track("visual_mode_selected", { count, template: templateId ?? "afarin" });
      if (!useSessionStore.getState().loaded) {
        await useSessionStore.getState().load();
      }
      if (useSessionStore.getState().session) {
        await api.startGeneration(detail.campaign.id);
        track("generation_started", { campaign_id: detail.campaign.id });
        router.push(`/campaigns/${detail.campaign.id}`);
        return;
      }
      router.push("/create/signup");
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[2]}
      backHref="/create/brief"
      heading={t("wizard.visualTitle")}
      description={t("wizard.visualDescription")}
      footer={
        <Button fullWidth size="lg" loading={saving} onClick={() => void handleGenerate()}>
          {t("wizard.buildCampaign")}
        </Button>
      }
    >
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-bold text-ink-700">{t("wizard.templateSection")}</h2>
        <p className="text-sm leading-7 text-muted">{t("wizard.templateOptional")}</p>
        <div className="grid max-h-[22rem] grid-cols-2 gap-2 overflow-y-auto pe-1">
          <ChoiceCard
            selected={templateId === null}
            title={t("wizard.afarinChooses")}
            description={t("wizard.afarinChoosesHint")}
            onSelect={() => setTemplateId(null)}
          />
          {templates
            ? templates.map((item) => (
                <ChoiceCard
                  key={item.id}
                  selected={templateId === item.id}
                  title={catalogLabel(locale, "templates", item.id, item.label_fa)}
                  description={catalogDescription(
                    locale,
                    "templates",
                    item.id,
                    item.description_fa,
                  )}
                  media={
                    item.preview_path ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={item.preview_path}
                        alt=""
                        className="aspect-4/5 w-full object-cover"
                      />
                    ) : undefined
                  }
                  onSelect={() => setTemplateId(item.id)}
                />
              ))
            : Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))}
        </div>
      </section>

      <TextAreaField
        label={t("wizard.instructionLabel")}
        hint={t("wizard.instructionHint")}
        optional
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder={t("wizard.instructionPlaceholder")}
        rows={3}
      />

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-bold text-ink-700">{t("wizard.imageCount")}</h2>
        <div className="grid grid-cols-2 gap-2">
          <ChoiceCard
            selected={count === 1}
            title={t("wizard.oneImage")}
            description={t("wizard.oneImageHint")}
            onSelect={() => setCount(1)}
          />
          <ChoiceCard
            selected={count === 3}
            title={t("wizard.threeImages")}
            description={t("wizard.threeImagesHint")}
            onSelect={() => setCount(3)}
          />
        </div>
      </section>
    </WizardShell>
  );
}
