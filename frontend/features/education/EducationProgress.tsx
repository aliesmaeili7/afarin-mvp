"use client";

import { Container } from "@/components/layout/Container";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Stepper";
import { formatPercent } from "@/lib/format/display";
import { generationStageMessage } from "@/lib/i18n/errors";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { EducationalPostStatusResponse } from "@/types/domain";

/**
 * One agent call and one image, so there is no per-asset checklist to show —
 * just the stage and the bar.
 */
export function EducationProgress({
  status,
}: {
  status: EducationalPostStatusResponse | null;
}) {
  const { t, locale } = useI18n();
  const percent = status?.percent ?? 0;

  return (
    <div className="min-h-dvh bg-background">
      <Container size="sm" className="flex min-h-dvh flex-col justify-center py-10">
        <div className="text-center">
          <div className="mx-auto grid size-16 place-items-center rounded-3xl bg-gradient-to-bl from-brand-600 via-brand-500 to-coral-500 text-white shadow-lift">
            <span className="animate-float text-2xl" aria-hidden="true">
              📚
            </span>
          </div>
          <h1 className="mt-5 text-2xl font-extrabold text-foreground">
            {t("education.generating")}
          </h1>
        </div>

        <Card className="mt-8 p-5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-semibold text-ink-700">
              {generationStageMessage(locale, status?.stage, status?.message_fa)}
            </span>
            <span className="text-sm font-bold tabular-nums text-brand-600">
              {formatPercent(percent, locale)}
            </span>
          </div>
          <div className="mt-3">
            <ProgressBar percent={percent} />
          </div>
        </Card>
      </Container>
    </div>
  );
}
