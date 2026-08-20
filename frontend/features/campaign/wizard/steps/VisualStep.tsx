"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { catalogDescription, catalogLabel } from "@/lib/i18n/catalog";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { Locale } from "@/lib/i18n/types";
import type {
  VisualCatalog,
  VisualCatalogEntry,
  VisualCreationMode,
  VisualRecipe,
} from "@/types/domain";
import { useSessionStore } from "@/features/auth/sessionStore";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

type Picker = "smart" | "custom";

export function VisualStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t, locale } = useI18n();
  const displayError = useDisplayError();
  const { detail, campaignId, loading, reload } = useDraftCampaign();
  const blocked = useWizardGuard(6, detail, loading, campaignId);

  const [mode, setMode] = useState<VisualCreationMode | null>(
    detail?.campaign.visual_creation_mode ?? null,
  );
  const [picker, setPicker] = useState<Picker>("smart");
  const [catalog, setCatalog] = useState<VisualCatalog | null>(null);
  const [proposals, setProposals] = useState<VisualRecipe[]>([]);
  const [styleId, setStyleId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [plannerError, setPlannerError] = useState<string | null>(null);
  const [plannerNeedsCrop, setPlannerNeedsCrop] = useState(false);

  useEffect(() => {
    void api
      .getVisualCatalog()
      .then(setCatalog)
      .catch((caught: unknown) => setCatalogError(displayError(caught)));
  }, [displayError]);

  useEffect(() => {
    const saved = detail?.campaign.visual_creation_mode;
    if (saved) setMode(saved);
  }, [detail?.campaign.visual_creation_mode]);

  async function persistMode(next: VisualCreationMode) {
    if (!campaignId) return;
    setMode(next);
    try {
      await api.updateCampaign(campaignId, { visual_creation_mode: next });
      await reload();
    } catch (caught) {
      toast(displayError(caught), "error");
    }
  }

  async function runPlanner() {
    if (!campaignId) return;
    setPlanning(true);
    setPlannerError(null);
    setPlannerNeedsCrop(false);
    try {
      const planned = await api.planVisuals(campaignId);
      if (planned.input_quality.status === "needs_fix") {
        setPlannerError(
          planned.input_quality.reasons[0]
            ? displayError(planned.input_quality.reasons[0])
            : t("errors.inputQualityNeedsFixShort"),
        );
        setPlannerNeedsCrop(true);
        return;
      }
      setProposals(planned.recipes);
    } catch (caught) {
      setPlannerError(displayError(caught));
    } finally {
      setPlanning(false);
    }
  }

  async function finish(recipe?: VisualRecipe) {
    if (!campaignId || !mode) return;
    setBusy(true);
    try {
      if (mode === "creative") {
        const chosen = recipe ?? customRecipe();
        if (!chosen) return;
        await api.saveVisualRecipe(campaignId, chosen);
      }
      track("visual_mode_selected", { mode });
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
      toast(displayError(caught), "error");
    } finally {
      setBusy(false);
    }
  }

  function customRecipe(): VisualRecipe | null {
    if (!styleId || !templateId) return null;
    const style = catalog?.styles.find((item) => item.id === styleId);
    const template = catalog?.templates.find((item) => item.id === templateId);
    return {
      style_id: styleId,
      template_id: templateId,
      source: "custom",
      title_fa: `${style?.label_fa ?? ""} × ${template?.label_fa ?? ""}`,
      description_fa: template?.description_fa,
      text_safe_area: template?.default_text_safe_area,
    };
  }

  const customReady = Boolean(styleId && templateId);

  return (
    <WizardShell
      step={WIZARD_STEPS[5]}
      backHref="/create/concepts"
      heading={t("wizard.visualTitle")}
      description={t("wizard.visualDescription")}
      footer={
        mode === "accurate" ? (
          <Button fullWidth size="lg" loading={busy} onClick={() => void finish()}>
            {t("wizard.buildCampaign")}
          </Button>
        ) : mode === "creative" && picker === "custom" ? (
          <Button
            fullWidth
            size="lg"
            loading={busy}
            disabled={!customReady}
            onClick={() => void finish()}
          >
            {t("wizard.buildCampaign")}
          </Button>
        ) : mode === "creative" ? (
          <p className="text-center text-sm text-muted">{t("wizard.pickProposal")}</p>
        ) : null
      }
    >
      {blocked || loading ? (
        <Skeleton className="h-48 w-full" />
      ) : catalogError ? (
        <ErrorState
          description={catalogError}
          action={
            <Button variant="outline" onClick={() => router.push("/create")}>
              {t("wizard.backToCrop")}
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          <ChoiceCard
            selected={mode === "accurate"}
            onSelect={() => void persistMode("accurate")}
            title={t("wizard.accurateTitle")}
            description={t("wizard.accurateDescription")}
          />
          <ChoiceCard
            selected={mode === "creative"}
            onSelect={() => void persistMode("creative")}
            title={t("wizard.creativeTitle")}
            description={t("wizard.creativeDescription")}
          />

          {mode === "creative" ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={picker === "smart" ? "primary" : "outline"}
                  onClick={() => setPicker("smart")}
                >
                  {t("wizard.letAfarin")}
                </Button>
                <Button
                  variant={picker === "custom" ? "primary" : "outline"}
                  onClick={() => setPicker("custom")}
                >
                  {t("wizard.illChoose")}
                </Button>
              </div>

              {picker === "smart" ? (
                <SmartPicker
                  locale={locale}
                  planning={planning}
                  proposals={proposals}
                  catalog={catalog}
                  error={plannerError}
                  needsCrop={plannerNeedsCrop}
                  onPlan={() => void runPlanner()}
                  onFixCrop={() => router.push("/create")}
                  onChoose={(recipe) => void finish(recipe)}
                  choosing={busy}
                />
              ) : (
                <CustomPicker
                  locale={locale}
                  catalog={catalog}
                  styleId={styleId}
                  templateId={templateId}
                  onStyle={setStyleId}
                  onTemplate={setTemplateId}
                />
              )}
            </>
          ) : null}
        </div>
      )}
    </WizardShell>
  );
}

function SmartPicker({
  locale,
  planning,
  proposals,
  catalog,
  error,
  needsCrop,
  onPlan,
  onFixCrop,
  onChoose,
  choosing,
}: {
  locale: Locale;
  planning: boolean;
  proposals: VisualRecipe[];
  catalog: VisualCatalog | null;
  error: string | null;
  needsCrop: boolean;
  onPlan: () => void;
  onFixCrop: () => void;
  onChoose: (recipe: VisualRecipe) => void;
  choosing: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-3">
      {error ? (
        <ErrorState
          description={error}
          action={
            needsCrop ? (
              <Button variant="outline" onClick={onFixCrop}>
                {t("wizard.backToCrop")}
              </Button>
            ) : (
              <Button variant="outline" loading={planning} onClick={onPlan}>
                {t("common.retry")}
              </Button>
            )
          }
        />
      ) : null}
      {proposals.length === 0 && !error ? (
        <Button fullWidth loading={planning} onClick={onPlan}>
          {t("wizard.threeProposals")}
        </Button>
      ) : null}
      {proposals.map((recipe) => (
        <ChoiceCard
          key={`${recipe.style_id}-${recipe.template_id}-${recipe.title_fa}`}
          selected={false}
          onSelect={() => onChoose(recipe)}
          title={
            recipe.title_fa ??
            catalogLabel(
              locale,
              "styles",
              recipe.style_id,
              entryOf(catalog, "styles", recipe.style_id)?.label_fa ?? recipe.style_id,
            )
          }
          description={recipe.description_fa}
          media={
            <PreviewPair
              style={entryOf(catalog, "styles", recipe.style_id)}
              template={entryOf(catalog, "templates", recipe.template_id)}
            />
          }
        />
      ))}
      {proposals.length > 0 ? (
        <Button variant="outline" loading={planning || choosing} onClick={onPlan}>
          {t("wizard.threeMore")}
        </Button>
      ) : null}
    </div>
  );
}

function CustomPicker({
  locale,
  catalog,
  styleId,
  templateId,
  onStyle,
  onTemplate,
}: {
  locale: Locale;
  catalog: VisualCatalog | null;
  styleId: string | null;
  templateId: string | null;
  onStyle: (id: string) => void;
  onTemplate: (id: string) => void;
}) {
  const { t } = useI18n();
  if (!catalog) return <Skeleton className="h-40 w-full" />;
  return (
    <div className="flex flex-col gap-5">
      <section>
        <h2 className="mb-2 text-sm font-bold text-ink-700">{t("wizard.styleSection")}</h2>
        <div className="grid grid-cols-2 gap-2">
          {catalog.styles.map((item) => (
            <CatalogCard
              key={item.id}
              locale={locale}
              kind="styles"
              item={item}
              selected={styleId === item.id}
              onSelect={() => onStyle(item.id)}
            />
          ))}
        </div>
      </section>
      <section>
        <h2 className="mb-2 text-sm font-bold text-ink-700">{t("wizard.templateSection")}</h2>
        <div className="grid grid-cols-2 gap-2">
          {catalog.templates.map((item) => (
            <CatalogCard
              key={item.id}
              locale={locale}
              kind="templates"
              item={item}
              selected={templateId === item.id}
              onSelect={() => onTemplate(item.id)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function CatalogCard({
  locale,
  kind,
  item,
  selected,
  onSelect,
}: {
  locale: Locale;
  kind: "styles" | "templates";
  item: VisualCatalogEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <ChoiceCard
      selected={selected}
      onSelect={onSelect}
      title={catalogLabel(locale, kind, item.id, item.label_fa)}
      description={catalogDescription(locale, kind, item.id, item.description_fa)}
      media={
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.preview_path}
          alt=""
          className="aspect-4/5 w-full object-cover"
        />
      }
    />
  );
}

function PreviewPair({
  style,
  template,
}: {
  style: VisualCatalogEntry | undefined;
  template: VisualCatalogEntry | undefined;
}) {
  return (
    <div className="grid grid-cols-2 gap-px bg-ink-100">
      {style ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={style.preview_path} alt="" className="aspect-4/5 w-full object-cover" />
      ) : null}
      {template ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={template.preview_path}
          alt=""
          className="aspect-4/5 w-full object-cover"
        />
      ) : null}
    </div>
  );
}

function entryOf(
  catalog: VisualCatalog | null,
  kind: "styles" | "templates",
  id: string,
) {
  return catalog?.[kind].find((item) => item.id === id);
}
