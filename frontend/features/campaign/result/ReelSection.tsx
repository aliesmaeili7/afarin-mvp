"use client";

import { Badge, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatDigits } from "@/lib/format/display";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { CampaignCopy, ReelConcept } from "@/types/domain";
import { SectionHeading } from "./AssetSection";

/** Spec §16 section 6 — storyboard only; video generation is a later phase. */
export function ReelSection({ copies }: { copies: CampaignCopy[] }) {
  const { t, locale } = useI18n();
  const entry = copies.find((item) => item.copy_type === "reel_concept");
  const reel = entry?.metadata_json?.reel as ReelConcept | undefined;

  if (!reel) return null;

  return (
    <section>
      <SectionHeading
        title={t("result.reelTitle")}
        description={t("result.reelDescription", {
          n: formatDigits(reel.duration_seconds, locale),
        })}
      />

      <Card className="divide-y divide-ink-100">
        <Block label={t("result.reelHook")} text={reel.hook_fa} />
        {reel.scenes_fa.map((scene, index) => (
          <Block
            key={scene}
            label={t("result.reelScene", { n: formatDigits(index + 1, locale) })}
            text={scene}
          />
        ))}
        <Block label={t("result.reelCta")} text={reel.cta_fa} />
        <Block label={t("result.reelVoice")} text={reel.voiceover_fa} />

        <div className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-ink-700">
              {t("result.reelVideoSoon")}
            </span>
            <Badge tone="warning">{t("result.comingSoon")}</Badge>
          </div>
          <Button variant="outline" size="sm" disabled>
            {t("result.makeVideo")}
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
