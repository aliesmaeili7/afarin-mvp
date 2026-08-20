"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/Feedback";
import { DownloadIcon, EditIcon, RefreshIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { AssetRenderSpec, CampaignAsset } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useAssetExport } from "@/features/campaign/ad-renderer/AssetExportProvider";

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
        <h2 className="text-lg font-extrabold text-foreground">{title}</h2>
        {description ? (
          <p className="mt-1 text-sm leading-7 text-muted">{description}</p>
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
  const { t } = useI18n();
  const displayError = useDisplayError();
  const { exportAsset, exporting } = useAssetExport();
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
      toast(t("result.downloadFailed"), "error");
    }
  }

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      await api.regenerateAsset(campaignId, asset.id);
      track("regeneration_requested", { asset_type: asset.asset_type });
      onChanged();
      toast(t("result.regenerated"));
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setRegenerating(false);
    }
  }

  if (spec.failed) {
    return (
      <section>
        <SectionHeading title={title} description={description} />
        <ErrorState
          title={t("result.sectionFailed")}
          description={
            allowRegenerate ? t("result.sectionFailedRetry") : t("result.sectionFailedRest")
          }
          action={
            allowRegenerate ? (
              <Button loading={regenerating} onClick={handleRegenerate}>
                {t("result.rebuild")}
              </Button>
            ) : null
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
        <div className="flex flex-wrap gap-2 border-t border-border p-3">
          <Button
            className="flex-1"
            loading={exporting}
            onClick={handleDownload}
            iconStart={<DownloadIcon width={18} height={18} />}
          >
            {t("common.download")}
          </Button>
          <Link
            href={`/campaigns/${campaignId}/assets/${asset.id}/edit`}
            className="flex-1"
          >
            <Button
              variant="outline"
              className="w-full"
              iconStart={<EditIcon width={18} height={18} />}
            >
              {t("common.editText")}
            </Button>
          </Link>
          {allowRegenerate ? (
            <Button
              variant="ghost"
              className="flex-1"
              loading={regenerating}
              onClick={handleRegenerate}
              iconStart={<RefreshIcon width={18} height={18} />}
            >
              {t("result.newVersion")}
            </Button>
          ) : null}
        </div>
      </Card>
    </section>
  );
}
