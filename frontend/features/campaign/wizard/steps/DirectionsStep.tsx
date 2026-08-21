"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RefreshIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { catalogLabel } from "@/lib/i18n/catalog";
import { formatDigits } from "@/lib/format/display";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import { ApiError } from "@/lib/api/types";
import type {
  CampaignConcept,
  VisualCatalog,
  VisualCreationMode,
  VisualRecipe,
} from "@/types/domain";
import { useSessionStore } from "@/features/auth/sessionStore";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { isLegacyDirection, WIZARD_STEPS } from "../wizardSteps";
import { CatalogPicker, PreviewPair, entryOf } from "./CatalogPicker";

export function DirectionsStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t, locale } = useI18n();
  const displayError = useDisplayError();
  const { detail, campaignId, loading, reload } = useDraftCampaign();
  const blocked = useWizardGuard(3, detail, loading, campaignId);

  const [generating, setGenerating] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsCrop, setNeedsCrop] = useState(false);
  const [catalog, setCatalog] = useState<VisualCatalog | null>(null);
  const [showCatalog, setShowCatalog] = useState(false);
  const requestedRef = useRef(false);

  const [mode, setMode] = useState<VisualCreationMode | null>(
    detail?.campaign.visual_creation_mode ?? null,
  );
  const [styleId, setStyleId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);

  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    void api
      .getVisualCatalog()
      .then(setCatalog)
      .catch((caught: unknown) => setError(displayError(caught)));
  }, [displayError]);

  useEffect(() => {
    const saved = detail?.campaign.visual_creation_mode;
    if (saved) setMode(saved);
  }, [detail?.campaign.visual_creation_mode]);

  const concepts = detail?.concepts ?? [];
  const selectedId = detail?.campaign.selected_concept_id ?? null;
  const recipe = recipeOf(detail?.campaign.visual_recipe_json);
  const recommended = recommendedOf(recipe);

  useEffect(() => {
    if (recipe?.style_id) setStyleId(recipe.style_id);
    if (recipe?.template_id) setTemplateId(recipe.template_id);
  }, [recipe?.style_id, recipe?.template_id]);

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
    setNeedsCrop(false);
    try {
      await api.generateConcepts(campaignId);
      await reload();
      track("concepts_generated");
    } catch (caught) {
      setError(displayError(caught));
      setNeedsCrop(isInputQualityError(caught));
    }
  }, [campaignId, reload, displayError]);

  useEffect(() => {
    requestedRef.current = false;
  }, [briefKey]);

  const legacy = concepts.some((concept) => isLegacyDirection(concept.raw_json));
  const needsDirections =
    !loading && !blocked && !error && (concepts.length === 0 || legacy);

  useEffect(() => {
    if (!needsDirections || requestedRef.current) return;
    requestedRef.current = true;
    void runGenerate();
  }, [needsDirections, runGenerate]);

  async function handleRegenerate() {
    setGenerating(true);
    setError(null);
    setShowCatalog(false);
    await runGenerate();
    setGenerating(false);
  }

  async function handleSelect(concept: CampaignConcept) {
    if (!campaignId) return;
    setSelecting(concept.id);
    try {
      const updated = await api.selectConcept(campaignId, concept.id);
      track("concept_selected", { concept_number: concept.concept_number });
      const next = recipeOf(updated.visual_recipe_json);
      if (next?.style_id) setStyleId(next.style_id);
      if (next?.template_id) setTemplateId(next.template_id);
      setShowCatalog(false);
      await reload();
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSelecting(null);
    }
  }

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

  async function finish() {
    if (!campaignId || !selectedId || !mode) {
      toast(t("wizard.chooseDirectionFirst"), "info");
      return;
    }
    if (mode === "creative" && (!styleId || !templateId)) {
      toast(t("wizard.pickProposal"), "info");
      return;
    }
    setBusy(true);
    try {
      if (mode === "creative" && styleId && templateId) {
        const changed =
          styleId !== recommended?.style_id || templateId !== recommended?.template_id;
        if (changed) {
          await api.saveVisualRecipe(campaignId, {
            style_id: styleId,
            template_id: templateId,
            source: "custom",
          });
        }
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

  const waiting = loading || blocked || generating || needsDirections;
  const canBuild =
    Boolean(selectedId && mode) &&
    (mode !== "creative" || Boolean(styleId && templateId));

  return (
    <WizardShell
      step={WIZARD_STEPS[2]}
      backHref="/create/brief"
      heading={waiting ? t("wizard.directionsBusyTitle") : t("wizard.directionsTitle")}
      description={
        waiting
          ? t("wizard.directionsBusyDescription")
          : t("wizard.directionsDescription")
      }
      footer={
        <>
          <Button
            fullWidth
            size="lg"
            loading={busy}
            disabled={!canBuild || waiting}
            onClick={() => void finish()}
          >
            {t("wizard.buildCampaign")}
          </Button>
          <Button
            fullWidth
            size="lg"
            variant="outline"
            loading={generating}
            disabled={waiting && !error}
            onClick={() => void handleRegenerate()}
            iconStart={<RefreshIcon width={18} height={18} />}
          >
            {t("wizard.conceptsRegen")}
          </Button>
        </>
      }
    >
      {error ? (
        <ErrorState
          description={error}
          action={
            needsCrop ? (
              <Button variant="outline" onClick={() => router.push("/create")}>
                {t("wizard.backToCrop")}
              </Button>
            ) : (
              <Button variant="outline" onClick={() => void handleRegenerate()}>
                {t("common.retry")}
              </Button>
            )
          }
        />
      ) : waiting ? (
        <DirectionsLoading />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            {concepts.map((concept) => {
              const meta = directionMeta(concept);
              return (
                <ChoiceCard
                  key={concept.id}
                  selected={concept.id === selectedId}
                  onSelect={() => void handleSelect(concept)}
                  title={
                    <span className="flex flex-col gap-1">
                      <span className="text-xs font-semibold text-brand-600">
                        {t("wizard.conceptBadge", {
                          n: formatDigits(concept.concept_number, locale),
                        })}
                      </span>
                      {concept.title_fa}
                    </span>
                  }
                  description={
                    <>
                      <span className="block font-medium text-ink-700">
                        {concept.headline_fa}
                      </span>
                      <span className="mt-1 block">{concept.description_fa}</span>
                      {meta.warningFa ? (
                        <span className="mt-1 block text-xs text-coral-600">
                          {meta.warningFa}
                        </span>
                      ) : null}
                    </>
                  }
                  media={
                    <PreviewPair
                      style={entryOf(catalog, "styles", meta.styleId)}
                      template={entryOf(catalog, "templates", meta.templateId)}
                    />
                  }
                />
              );
            })}
          </div>

          {selectedId ? (
            <section className="flex flex-col gap-3">
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
            </section>
          ) : null}

          {selectedId && mode === "creative" ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-bold text-ink-700">
                {t("wizard.recommendedRecipe")}
              </h2>
              {styleId && templateId ? (
                <div className="overflow-hidden rounded-3xl border border-border">
                  <PreviewPair
                    style={entryOf(catalog, "styles", styleId)}
                    template={entryOf(catalog, "templates", templateId)}
                  />
                  <p className="p-3 text-sm text-muted">
                    {catalogLabel(
                      locale,
                      "styles",
                      styleId,
                      entryOf(catalog, "styles", styleId)?.label_fa ?? styleId,
                    )}
                    {" × "}
                    {catalogLabel(
                      locale,
                      "templates",
                      templateId,
                      entryOf(catalog, "templates", templateId)?.label_fa ??
                        templateId,
                    )}
                  </p>
                </div>
              ) : (
                <Skeleton className="h-32 w-full" />
              )}
              <Button
                variant="outline"
                onClick={() => setShowCatalog((current) => !current)}
              >
                {showCatalog ? t("wizard.hideCatalog") : t("wizard.changeStyle")}
              </Button>
              {showCatalog ? (
                <CatalogPicker
                  locale={locale}
                  catalog={catalog}
                  styleId={styleId}
                  templateId={templateId}
                  onStyle={setStyleId}
                  onTemplate={setTemplateId}
                />
              ) : null}
            </section>
          ) : null}

          {selecting ? (
            <p className="text-center text-sm text-muted">{t("common.loading")}</p>
          ) : null}
        </div>
      )}
    </WizardShell>
  );
}

function DirectionsLoading() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-brand-700">
        <span className="size-4 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        {t("wizard.conceptsLoading")}
      </p>
      {Array.from({ length: 3 }, (_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-3xl border border-border bg-surface"
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

function recipeOf(value: VisualRecipe | Record<string, unknown> | undefined) {
  if (!value || typeof value !== "object") return null;
  const recipe = value as VisualRecipe;
  if (!recipe.style_id || !recipe.template_id) return null;
  return recipe;
}

function recommendedOf(recipe: VisualRecipe | null) {
  if (!recipe) return null;
  const rec = recipe.recommended;
  if (rec?.style_id && rec.template_id) return rec;
  return { style_id: recipe.style_id, template_id: recipe.template_id };
}

function directionMeta(concept: CampaignConcept) {
  const raw = concept.raw_json ?? {};
  return {
    styleId: typeof raw.style_id === "string" ? raw.style_id : "",
    templateId: typeof raw.template_id === "string" ? raw.template_id : "",
    warningFa: typeof raw.warning_fa === "string" ? raw.warning_fa : "",
  };
}

function isInputQualityError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.messageFa.includes("کادر رو درست کن")
  );
}
