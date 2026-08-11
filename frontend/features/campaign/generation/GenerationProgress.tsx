"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Stepper";
import { CheckIcon } from "@/components/ui/icons";
import { cn } from "@/components/ui/cn";
import { toPersianDigits } from "@/lib/format/persian";
import { GENERATION_STAGES } from "@/lib/api/mock/generation";
import type { CampaignStatusResponse } from "@/types/domain";

const POLL_INTERVAL_MS = 1200;

/**
 * Spec §12 — a staged progress experience rather than a spinner.
 *
 * Progress is polled from the campaign status endpoint, so closing the tab and
 * coming back resumes wherever the job actually is.
 */
export function GenerationProgress({
  campaignId,
  onFinished,
}: {
  campaignId: string;
  onFinished: () => void;
}) {
  const [status, setStatus] = useState<CampaignStatusResponse | null>(null);
  const finishedRef = useRef(false);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const next = await api.getCampaignStatus(campaignId);
        if (!active) return;
        setStatus(next);

        const settled =
          next.status === "ready" ||
          next.status === "partial_failed" ||
          next.status === "failed";

        if (settled && !finishedRef.current) {
          finishedRef.current = true;
          if (next.status !== "failed") {
            track("campaign_completed", { campaign_id: campaignId });
          }
          // Let the bar visibly reach 100% before switching views.
          timer = setTimeout(onFinished, 700);
          return;
        }
      } catch {
        // Transient read failures should not kill the poll loop.
      }
      if (active) timer = setTimeout(poll, POLL_INTERVAL_MS);
    }

    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [campaignId, onFinished]);

  const activeIndex = GENERATION_STAGES.findIndex(
    (stage) => stage.stage === status?.stage,
  );
  const percent = status?.percent ?? 0;

  return (
    <div className="min-h-dvh bg-ink-50">
      <Container size="sm" className="flex min-h-dvh flex-col justify-center py-10">
        <div className="text-center">
          <div className="mx-auto grid size-16 place-items-center rounded-3xl bg-gradient-to-bl from-brand-600 via-brand-500 to-coral-500 text-white shadow-lift">
            <span className="animate-float text-2xl" aria-hidden="true">
              ✨
            </span>
          </div>
          <h1 className="mt-5 text-2xl font-extrabold text-ink-900">
            داریم کمپینت رو می‌سازیم
          </h1>
          <p className="mt-2 text-sm leading-7 text-ink-500">
            معمولاً کمتر از یک دقیقه طول می‌کشه. می‌تونی این صفحه رو ببندی؛ ساخت
            کمپین ادامه پیدا می‌کنه.
          </p>
        </div>

        <Card className="mt-8 p-5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-semibold text-ink-700">
              {status?.message_fa ?? "در حال آماده‌سازی…"}
            </span>
            <span className="text-sm font-bold tabular-nums text-brand-600">
              ٪{toPersianDigits(percent)}
            </span>
          </div>
          <div className="mt-3">
            <ProgressBar percent={percent} />
          </div>

          <ul className="mt-6 flex flex-col gap-3">
            {GENERATION_STAGES.map((stage, index) => {
              const done = activeIndex > index || percent === 100;
              const current = activeIndex === index && percent < 100;
              return (
                <li key={stage.stage} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "grid size-6 shrink-0 place-items-center rounded-full border-2 transition-colors",
                      done
                        ? "border-mint-500 bg-mint-500 text-white"
                        : current
                          ? "border-brand-500 text-brand-600"
                          : "border-ink-200 text-transparent",
                    )}
                  >
                    {done ? (
                      <CheckIcon width={13} height={13} strokeWidth={3} />
                    ) : current ? (
                      <span className="size-2 animate-pulse rounded-full bg-brand-500" />
                    ) : null}
                  </span>
                  <span
                    className={cn(
                      "text-sm",
                      done
                        ? "text-ink-400 line-through decoration-ink-300"
                        : current
                          ? "font-semibold text-ink-900"
                          : "text-ink-400",
                    )}
                  >
                    {stage.message_fa}
                  </span>
                </li>
              );
            })}
          </ul>
        </Card>
      </Container>
    </div>
  );
}
