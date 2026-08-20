"use client";

import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import type { RewriteIntent } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { normalizePersian } from "@/lib/format/persian";
import type { AssetRenderSpec, CampaignAsset } from "@/types/domain";
import { ASSET_REWRITE_CHIPS, RewriteChips } from "./RewriteChips";

/** Text stays editable before export (spec §15). */
export function EditTextSheet({
  asset,
  campaignId,
  open,
  onClose,
  onSaved,
}: {
  asset: CampaignAsset;
  campaignId: string;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  return (
    <Sheet open={open} onClose={onClose} title="ویرایش متن تبلیغ">
      {/* The sheet unmounts when closed, so the form always opens seeded with
          the asset's current text. */}
      <EditTextForm
        asset={asset}
        campaignId={campaignId}
        onClose={onClose}
        onSaved={onSaved}
      />
    </Sheet>
  );
}

function EditTextForm({
  asset,
  campaignId,
  onClose,
  onSaved,
}: {
  asset: CampaignAsset;
  campaignId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const spec = asset.metadata_json as AssetRenderSpec;

  const [headline, setHeadline] = useState(spec.headline_fa);
  const [subheadline, setSubheadline] = useState(spec.subheadline_fa ?? "");
  const [price, setPrice] = useState(spec.price_text ?? "");
  const [cta, setCta] = useState(spec.cta_fa ?? "");
  const [saving, setSaving] = useState(false);
  const [rewriting, setRewriting] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateAssetText(campaignId, asset.id, {
        headline_fa: normalizePersian(headline).trim(),
        subheadline_fa: normalizePersian(subheadline).trim() || null,
        price_text: normalizePersian(price).trim() || null,
        cta_fa: normalizePersian(cta).trim() || null,
      });
      onSaved();
      onClose();
      toast("متن‌ها به‌روز شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleRewrite(intent: RewriteIntent) {
    setRewriting(true);
    try {
      const updated = await api.rewriteAssetText(campaignId, asset.id, intent);
      const next = updated.metadata_json as AssetRenderSpec;
      setHeadline(next.headline_fa);
      setCta(next.cta_fa ?? "");
      onSaved();
      toast("متن جدید آماده شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setRewriting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <TextAreaField
        label="تیتر اصلی"
        rows={2}
        value={headline}
        onChange={(event) => setHeadline(event.target.value)}
      />
      <TextAreaField
        label="توضیح کوتاه"
        optional
        rows={2}
        value={subheadline}
        onChange={(event) => setSubheadline(event.target.value)}
      />
      <TextField
        label="قیمت یا تخفیف"
        optional
        value={price}
        onChange={(event) => setPrice(event.target.value)}
      />
      <TextField
        label="دعوت به اقدام"
        optional
        value={cta}
        onChange={(event) => setCta(event.target.value)}
      />

      <RewriteChips
        chips={ASSET_REWRITE_CHIPS}
        onSelect={(intent) => void handleRewrite(intent)}
        disabled={rewriting || saving}
      />

      <div className="mt-2 flex gap-2">
        <Button variant="outline" onClick={onClose} className="flex-1">
          انصراف
        </Button>
        <Button loading={saving} onClick={handleSave} className="flex-1">
          ذخیره
        </Button>
      </div>
    </div>
  );
}
