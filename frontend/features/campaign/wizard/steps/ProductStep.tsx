"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { useToast } from "@/components/ui/Toast";
import { normalizePersian } from "@/lib/format/persian";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import { useDraftCampaign } from "../useDraftCampaign";
import { useWizardGuard } from "../useWizardGuard";
import { WizardShell } from "../WizardShell";
import { WIZARD_STEPS } from "../wizardSteps";

interface FormState {
  name: string;
  description: string;
  price_text: string;
  main_benefit: string;
  brand_name: string;
}

const EMPTY: FormState = {
  name: "",
  description: "",
  price_text: "",
  main_benefit: "",
  brand_name: "",
};

export function ProductStep() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { detail, campaignId, loading } = useDraftCampaign();
  const blocked = useWizardGuard(2, detail, loading, campaignId);

  const [form, setForm] = useHydratedForm<FormState>(
    detail?.campaign.id ?? null,
    () => ({
      name: detail?.product?.name ?? "",
      description: detail?.product?.description ?? "",
      price_text: detail?.product?.price_text ?? "",
      main_benefit: detail?.product?.main_benefit ?? "",
      brand_name: detail?.brand?.name ?? "",
    }),
    EMPTY,
  );
  const [nameError, setNameError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  function update(key: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
    if (key === "name" && value.trim()) setNameError(null);
  }

  async function handleContinue() {
    if (!detail) return;
    if (!form.name.trim()) {
      setNameError(t("errors.productNameRequired"));
      return;
    }

    setSaving(true);
    try {
      await api.saveProduct(detail.campaign.id, {
        name: normalizePersian(form.name),
        description: normalizePersian(form.description),
        price_text: normalizePersian(form.price_text),
        main_benefit: normalizePersian(form.main_benefit),
        brand_name: normalizePersian(form.brand_name),
      });
      router.push("/create/objective");
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WizardShell
      step={WIZARD_STEPS[1]}
      backHref="/create"
      heading={t("wizard.productTitle")}
      description={t("wizard.productDescription")}
      footer={
        <Button fullWidth size="lg" loading={saving} onClick={handleContinue}>
          {t("common.continue")}
        </Button>
      }
    >
      {loading || blocked ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <TextField
            label={t("wizard.productName")}
            placeholder={t("wizard.productNamePlaceholder")}
            value={form.name}
            error={nameError}
            onChange={(event) => update("name", event.target.value)}
          />

          <TextAreaField
            label={t("wizard.productDesc")}
            optional
            placeholder={t("wizard.productDescPlaceholder")}
            value={form.description}
            onChange={(event) => update("description", event.target.value)}
          />

          <TextField
            label={t("wizard.productPrice")}
            optional
            placeholder={t("wizard.productPricePlaceholder")}
            hint={t("wizard.productPriceHint")}
            value={form.price_text}
            onChange={(event) => update("price_text", event.target.value)}
          />

          <TextAreaField
            label={t("wizard.productBenefit")}
            optional
            rows={2}
            placeholder={t("wizard.productBenefitPlaceholder")}
            value={form.main_benefit}
            onChange={(event) => update("main_benefit", event.target.value)}
          />

          <TextField
            label={t("wizard.productBrand")}
            optional
            placeholder={t("wizard.productBrandPlaceholder")}
            hint={t("wizard.productBrandHint")}
            value={form.brand_name}
            onChange={(event) => update("brand_name", event.target.value)}
          />

          <div className="rounded-2xl border border-border bg-surface p-4">
            <button
              type="button"
              onClick={() => setShowExamples((current) => !current)}
              className="text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              {t("wizard.productHelpToggle")}
            </button>
            {showExamples ? (
              <ul className="mt-3 flex flex-col gap-2 text-sm leading-7 text-muted">
                <li>
                  <span className="font-semibold text-ink-700">
                    {t("wizard.productHelpDescLabel")}
                  </span>{" "}
                  {t("wizard.productHelpDesc")}
                </li>
                <li>
                  <span className="font-semibold text-ink-700">
                    {t("wizard.productHelpBenefitLabel")}
                  </span>{" "}
                  {t("wizard.productHelpBenefit")}
                </li>
                <li>
                  <span className="font-semibold text-ink-700">
                    {t("wizard.productHelpPriceLabel")}
                  </span>{" "}
                  {t("wizard.productHelpPrice")}
                </li>
              </ul>
            ) : null}
          </div>
        </div>
      )}
    </WizardShell>
  );
}
