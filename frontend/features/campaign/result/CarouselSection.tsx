"use client";

import { useState } from "react";
import Link from "next/link";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DownloadIcon, EditIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { formatDigits } from "@/lib/format/display";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { AssetRenderSpec, CampaignAsset } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useAssetExport } from "@/features/campaign/ad-renderer/AssetExportProvider";
import { SectionHeading } from "./AssetSection";

/** Spec §16 section 3 — three slides, each individually downloadable. */
export function CarouselSection({
  slides,
  campaignId,
}: {
  slides: CampaignAsset[];
  campaignId: string;
}) {
  const { toast } = useToast();
  const { t, locale } = useI18n();
  const { exportAsset } = useAssetExport();
  const [downloading, setDownloading] = useState<string | null>(null);

  async function downloadSlide(asset: CampaignAsset) {
    setDownloading(asset.id);
    try {
      await exportAsset({
        spec: asset.metadata_json as AssetRenderSpec,
        width: asset.width,
        height: asset.height,
        filename: `afarin-${asset.asset_type}.png`,
      });
      track("asset_downloaded", { asset_type: asset.asset_type });
    } catch {
      toast(t("result.downloadFailed"), "error");
    } finally {
      setDownloading(null);
    }
  }

  async function downloadAll() {
    setDownloading("all");
    try {
      for (const slide of slides) {
        await exportAsset({
          spec: slide.metadata_json as AssetRenderSpec,
          width: slide.width,
          height: slide.height,
          filename: `afarin-${slide.asset_type}.png`,
        });
        track("asset_downloaded", { asset_type: slide.asset_type });
      }
    } catch {
      toast(t("result.downloadAllFailed"), "error");
    } finally {
      setDownloading(null);
    }
  }

  if (slides.length === 0) return null;

  return (
    <section>
      <SectionHeading
        title={t("result.carouselTitle")}
        description={t("result.carouselDescription")}
        action={
          <Button
            size="sm"
            variant="outline"
            loading={downloading === "all"}
            onClick={downloadAll}
            iconStart={<DownloadIcon width={16} height={16} />}
          >
            {t("result.downloadAll")}
          </Button>
        }
      />

      <div className="no-scrollbar -mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-3 sm:px-0">
        {slides.map((slide, index) => (
          <Card
            key={slide.id}
            className="w-[68%] shrink-0 snap-center overflow-hidden sm:w-auto"
          >
            <div className="p-2">
              <div className="overflow-hidden rounded-xl">
                <AdCanvas
                  spec={slide.metadata_json as AssetRenderSpec}
                  width={slide.width}
                  height={slide.height}
                  storagePath={slide.storage_path}
                />
              </div>
            </div>
            <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-2">
              <span className="text-xs font-semibold text-muted">
                {t("result.slideN", { n: formatDigits(index + 1, locale) })}
              </span>
              <div className="flex items-center gap-1">
                <Link
                  href={`/campaigns/${campaignId}/assets/${slide.id}/edit`}
                  aria-label={t("result.editSlide", {
                    n: formatDigits(index + 1, locale),
                  })}
                >
                  <Button size="sm" variant="ghost" className="size-11 p-0 sm:size-9">
                    <EditIcon width={17} height={17} />
                  </Button>
                </Link>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={t("result.downloadSlide", {
                    n: formatDigits(index + 1, locale),
                  })}
                  loading={downloading === slide.id}
                  onClick={() => downloadSlide(slide)}
                  className="size-11 p-0 sm:size-9"
                >
                  <DownloadIcon width={17} height={17} />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
