"use client";

import Link from "next/link";
import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
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
  const [name, setName] = useState(detail.brand?.name ?? "");
  const [saving, setSaving] = useState(false);

  const savedBrand = detail.brand;

  async function handleSave() {
    if (!name.trim()) {
      toast("اسم برند رو بنویس.", "error");
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
      toast("برندت ذخیره شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  if (savedBrand) {
    return (
      <Card className="flex flex-col gap-3 bg-brand-50/60 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-bold text-ink-900">
            برند «{savedBrand.name}» ذخیره شده
          </h3>
          <p className="mt-1 text-sm leading-7 text-ink-500">
            کمپین بعدی‌ات با همین اطلاعات سریع‌تر ساخته می‌شه.
          </p>
        </div>
        <Link href={`/brands/${savedBrand.id}`} className="shrink-0">
          <Button variant="outline">مشاهده برند</Button>
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
          <h3 className="text-base font-bold text-ink-900">
            این اطلاعات رو برای کمپین بعدی ذخیره کنیم؟
          </h3>
          <p className="mt-1 text-sm leading-7 text-ink-500">
            دفعه بعد دیگه لازم نیست مخاطب و سبک تبلیغ رو دوباره وارد کنی.
          </p>
        </div>
      </div>

      <TextField
        label="اسم برند یا کسب‌وکار"
        placeholder="مثلاً سحند"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />

      <Button loading={saving} onClick={handleSave}>
        ذخیره برند
      </Button>
    </Card>
  );
}
