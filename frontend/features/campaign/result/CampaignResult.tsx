"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/Container";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Card";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { PlusIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { toPersianError } from "@/lib/api";
import type { CampaignAsset, CampaignDetail } from "@/types/domain";
import { BrandKitPrompt } from "@/features/brand/BrandKitPrompt";
import { beginNewCampaign } from "@/features/campaign/wizard/useWizardStore";
import { AssetSection } from "./AssetSection";
import { CaptionsSection } from "./CaptionsSection";
import { CarouselSection } from "./CarouselSection";
import { ReelSection } from "./ReelSection";
import { StoryIdeasSection } from "./StoryIdeasSection";

/** Spec §16 — the most important page in the application. */
export function CampaignResult({
  detail,
  onChanged,
}: {
  detail: CampaignDetail;
  onChanged: () => void;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [starting, setStarting] = useState(false);

  const byType = (type: CampaignAsset["asset_type"]) =>
    detail.assets.find((asset) => asset.asset_type === type);

  const feed = byType("feed_final");
  const story = byType("story_final");
  const carousel = (["carousel_1", "carousel_2", "carousel_3"] as const)
    .map(byType)
    .filter((asset): asset is CampaignAsset => Boolean(asset));

  return (
    <div className="min-h-dvh bg-ink-50">
      <SiteHeader />

      <Container size="md" className="flex flex-col gap-10 py-8">
        <header className="text-center">
          <Badge tone="success">آماده انتشار</Badge>
          <h1 className="mt-3 text-3xl font-extrabold text-ink-900">
            کمپینت آماده‌ست ✨
          </h1>
          <p className="mt-2 text-sm leading-7 text-ink-500">
            {detail.product?.name
              ? `پکیج تبلیغاتی «${detail.product.name}» شامل پست، استوری، کاروسل، کپشن و ایده ریلز.`
              : "پکیج تبلیغاتی اینستاگرام شامل پست، استوری، کاروسل، کپشن و ایده ریلز."}
          </p>
          {(feed?.metadata_json as { product_source?: string } | undefined)
            ?.product_source === "crop" ? (
            <p className="mt-3 rounded-2xl bg-brand-50 px-4 py-3 text-sm leading-7 text-ink-600">
              پس‌زمینه عکس حذف نشد؛ محصول از همان کادری که انتخاب کردی روی صحنه
              گذاشته شد.
            </p>
          ) : null}
        </header>

        {feed ? (
          <AssetSection
            asset={feed}
            campaignId={detail.campaign.id}
            title="پست فید"
            description="نسبت ۴:۵، مناسب صفحه اصلی اینستاگرام."
            allowRegenerate
            onChanged={onChanged}
          />
        ) : null}

        {story ? (
          <AssetSection
            asset={story}
            campaignId={detail.campaign.id}
            title="استوری"
            description="نسبت ۹:۱۶، جداگانه برای حالت عمودی چیده شده."
            previewClassName="mx-auto w-full max-w-[16rem] p-4"
            allowRegenerate
            onChanged={onChanged}
          />
        ) : null}

        <CarouselSection slides={carousel} />

        <CaptionsSection
          campaignId={detail.campaign.id}
          copies={detail.copies}
          onChanged={onChanged}
        />

        <StoryIdeasSection copies={detail.copies} />

        <ReelSection copies={detail.copies} />

        <BrandKitPrompt detail={detail} onSaved={onChanged} />

        <div className="flex flex-col gap-3 border-t border-ink-100 pt-8 sm:flex-row">
          <Button
            fullWidth
            variant="outline"
            size="lg"
            className="flex-1"
            loading={starting}
            iconStart={<PlusIcon width={18} height={18} />}
            onClick={() => {
              setStarting(true);
              void beginNewCampaign()
                .then(() => router.push("/create"))
                .catch((caught: unknown) => {
                  toast(toPersianError(caught), "error");
                  setStarting(false);
                });
            }}
          >
            ساخت کمپین جدید
          </Button>
          <Link href="/dashboard" className="flex-1">
            <Button fullWidth variant="ghost" size="lg">
              رفتن به داشبورد
            </Button>
          </Link>
        </div>
      </Container>
    </div>
  );
}
