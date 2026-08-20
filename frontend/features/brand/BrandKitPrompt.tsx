"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { CampaignDetail } from "@/types/domain";

/**
 * Spec §18 — after the first successful campaign, offer to remember what we
 * already know so the next campaign starts further along.
 */
export function BrandKitPrompt({
  detail,
  onSaved,
}: {
  detail: CampaignDetail;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const [name, setName] = useState(detail.brand?.name ?? "");
  const [saving, setSaving] = useState(false);

  const savedBrand = detail.brand;

  async function handleSave() {
    if (!name.trim()) {
      toast(t("errors.brandNameRequired"), "error");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        description: detail.product?.description ?? null,
        target_audience: detail.campaign.audience,
        visual_style: detail.campaign.visual_style,
        tone: detail.campaign.visual_style,
      };

      if (savedBrand) {
        await api.updateBrand(savedBrand.id, payload);
      } else {
        const brand = await api.createBrand(payload);
        await api.updateCampaign(detail.campaign.id, { brand_id: brand.id });
      }

      track("brand_saved");
      onSaved();
      toast(t("brand.brandSaved"));
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  if (savedBrand) {
    return (
      <Card className="flex flex-col gap-3 bg-brand-50/60 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-bold text-foreground">
            {t("brand.promptSavedTitle", { name: savedBrand.name })}
          </h3>
          <p className="mt-1 text-sm leading-7 text-muted">{t("brand.promptSavedBody")}</p>
        </div>
        <Link href={`/brands/${savedBrand.id}`} className="shrink-0">
          <Button variant="outline">{t("brand.viewBrand")}</Button>
        </Link>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-4 bg-brand-50/60 p-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-brand-600">
          <SparkleIcon width={20} height={20} />
        </span>
        <div>
          <h3 className="text-base font-bold text-foreground">{t("brand.promptTitle")}</h3>
          <p className="mt-1 text-sm leading-7 text-muted">{t("brand.promptBody")}</p>
        </div>
      </div>

      <TextField
        label={t("wizard.productBrand")}
        placeholder={t("wizard.productBrandPlaceholder")}
        value={name}
        onChange={(event) => setName(event.target.value)}
      />

      <Button loading={saving} onClick={handleSave}>
        {t("brand.saveBrand")}
      </Button>
    </Card>
  );
}
