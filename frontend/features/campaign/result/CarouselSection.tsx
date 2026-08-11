"use client";

import { useState } from "react";
import { track } from "@/lib/analytics/track";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DownloadIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { toPersianDigits } from "@/lib/format/persian";
import type { AssetRenderSpec, CampaignAsset } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useAssetExport } from "@/features/campaign/ad-renderer/AssetExportProvider";
import { SectionHeading } from "./AssetSection";

/** Spec §16 section 3 — three slides, each individually downloadable. */
export function CarouselSection({ slides }: { slides: CampaignAsset[] }) {
  const { toast } = useToast();
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
      toast("دانلود انجام نشد. دوباره امتحان کن.", "error");
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
      toast("دانلود همه انجام نشد. دوباره امتحان کن.", "error");
    } finally {
      setDownloading(null);
    }
  }

  if (slides.length === 0) return null;

  return (
    <section>
      <SectionHeading
        title="کاروسل سه‌اسلایدی"
        description="اسلاید اول قلاب، دومی مزیت محصول و سومی دعوت به خرید."
        action={
          <Button
            size="sm"
            variant="outline"
            loading={downloading === "all"}
            onClick={downloadAll}
            iconStart={<DownloadIcon width={16} height={16} />}
          >
            دانلود همه
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
            <div className="flex items-center justify-between gap-2 border-t border-ink-100 px-3 py-2">
              <span className="text-xs font-semibold text-ink-500">
                اسلاید {toPersianDigits(index + 1)}
              </span>
              <Button
                size="sm"
                variant="ghost"
                aria-label={`دانلود اسلاید ${index + 1}`}
                loading={downloading === slide.id}
                onClick={() => downloadSlide(slide)}
                className="size-11 p-0 sm:size-9"
              >
                <DownloadIcon width={17} height={17} />
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
