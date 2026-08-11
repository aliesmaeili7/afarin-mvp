"use client";

import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import { ArrowForwardIcon } from "@/components/ui/icons";
import type { LandingExample } from "@/lib/content/landingExamples";

/**
 * Shows the transformation instead of describing it (spec §6): an ordinary
 * product photo on one side, the composed Persian ad on the other.
 */
export function BeforeAfter({ example }: { example: LandingExample }) {
  const rawUrl = useResolvedAssetUrl(example.product_image_path);

  return (
    <div className="flex items-center gap-2 sm:gap-4">
      <figure className="flex-1">
        <div className="relative aspect-4/5 overflow-hidden rounded-3xl border border-ink-200 bg-white">
          <span className="absolute top-3 start-3 z-10 rounded-full bg-ink-900/70 px-2.5 py-1 text-[0.65rem] font-semibold text-white">
            عکس معمولی
          </span>
          {rawUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={rawUrl}
              alt="عکس معمولی محصول"
              className="h-full w-full object-contain p-6"
            />
          ) : null}
        </div>
      </figure>

      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-600 text-white shadow-soft sm:size-9">
        <ArrowForwardIcon width={18} height={18} />
      </span>

      <figure className="flex-[1.25]">
        <div className="relative overflow-hidden rounded-3xl shadow-lift">
          <span className="absolute top-3 start-3 z-10 rounded-full bg-brand-600 px-2.5 py-1 text-[0.65rem] font-semibold text-white">
            تبلیغ آماده
          </span>
          <AdCanvas spec={example.spec} width={1080} height={1350} />
        </div>
      </figure>
    </div>
  );
}
