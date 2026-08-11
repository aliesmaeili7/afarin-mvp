"use client";

import { useState, type ReactNode } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/Feedback";
import { DownloadIcon, EditIcon, RefreshIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import type { AssetRenderSpec, CampaignAsset } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useAssetExport } from "@/features/campaign/ad-renderer/AssetExportProvider";
import { EditTextSheet } from "./EditTextSheet";

export function SectionHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-extrabold text-ink-900">{title}</h2>
        {description ? (
          <p className="mt-1 text-sm leading-7 text-ink-500">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function AssetSection({
  asset,
  campaignId,
  title,
  description,
  previewClassName,
  allowRegenerate = false,
  onChanged,
}: {
  asset: CampaignAsset;
  campaignId: string;
  title: string;
  description?: string;
  previewClassName?: string;
  allowRegenerate?: boolean;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const { exportAsset, exporting } = useAssetExport();
  const [editing, setEditing] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const spec = asset.metadata_json as AssetRenderSpec;

  async function handleDownload() {
    try {
      await exportAsset({
        spec,
        width: asset.width,
        height: asset.height,
        filename: `afarin-${asset.asset_type}.png`,
      });
      track("asset_downloaded", { asset_type: asset.asset_type });
    } catch {
      toast("دانلود انجام نشد. دوباره امتحان کن.", "error");
    }
  }

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      await api.regenerateAsset(campaignId, asset.id);
      track("regeneration_requested", { asset_type: asset.asset_type });
      onChanged();
      toast("یک نسخه تازه ساخته شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setRegenerating(false);
    }
  }

  if (spec.failed) {
    return (
      <section>
        <SectionHeading title={title} description={description} />
        <ErrorState
          title="این بخش ساخته نشد"
          description="بقیه کمپینت آماده‌ست. می‌تونی فقط همین بخش رو دوباره بسازی."
          action={
            <Button loading={regenerating} onClick={handleRegenerate}>
              ساخت دوباره
            </Button>
          }
        />
      </section>
    );
  }

  return (
    <section>
      <SectionHeading title={title} description={description} />
      <Card className="overflow-hidden">
        <div className={previewClassName ?? "mx-auto w-full max-w-sm p-4"}>
          <div className="overflow-hidden rounded-2xl shadow-soft">
            <AdCanvas
              spec={spec}
              width={asset.width}
              height={asset.height}
              storagePath={asset.storage_path}
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2 border-t border-ink-100 p-3">
          <Button
            className="flex-1"
            loading={exporting}
            onClick={handleDownload}
            iconStart={<DownloadIcon width={18} height={18} />}
          >
            دانلود
          </Button>
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => setEditing(true)}
            iconStart={<EditIcon width={18} height={18} />}
          >
            ویرایش متن
          </Button>
          {allowRegenerate ? (
            <Button
              variant="ghost"
              className="flex-1"
              loading={regenerating}
              onClick={handleRegenerate}
              iconStart={<RefreshIcon width={18} height={18} />}
            >
              نسخه جدید
            </Button>
          ) : null}
        </div>
      </Card>

      <EditTextSheet
        asset={asset}
        campaignId={campaignId}
        open={editing}
        onClose={() => setEditing(false)}
        onSaved={onChanged}
      />
    </section>
  );
}
