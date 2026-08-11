"use client";

import { Badge, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { toPersianDigits } from "@/lib/format/persian";
import type { CampaignCopy, ReelConcept } from "@/types/domain";
import { SectionHeading } from "./AssetSection";

/** Spec §16 section 6 — storyboard only; video generation is a later phase. */
export function ReelSection({ copies }: { copies: CampaignCopy[] }) {
  const entry = copies.find((item) => item.copy_type === "reel_concept");
  const reel = entry?.metadata_json?.reel as ReelConcept | undefined;

  if (!reel) return null;

  return (
    <section>
      <SectionHeading
        title="ایده ریلز"
        description={`یک ریلز کوتاه ${toPersianDigits(reel.duration_seconds)} ثانیه‌ای.`}
      />

      <Card className="divide-y divide-ink-100">
        <Block label="قلاب شروع" text={reel.hook_fa} />
        {reel.scenes_fa.map((scene, index) => (
          <Block
            key={scene}
            label={`صحنه ${toPersianDigits(index + 1)}`}
            text={scene}
          />
        ))}
        <Block label="دعوت به اقدام" text={reel.cta_fa} />
        <Block label="متن گوینده" text={reel.voiceover_fa} />

        <div className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-ink-700">
              این ایده رو به ویدیو تبدیل کن
            </span>
            <Badge tone="warning">به‌زودی</Badge>
          </div>
          <Button variant="outline" size="sm" disabled>
            ساخت ویدیو
          </Button>
        </div>
      </Card>
    </section>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex flex-col gap-1 p-4 sm:flex-row sm:gap-4">
      <span className="w-28 shrink-0 text-xs font-bold text-brand-600">
        {label}
      </span>
      <p className="text-sm leading-8 text-ink-800">{text}</p>
    </div>
  );
}
