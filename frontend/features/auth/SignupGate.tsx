"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Feedback";
import { Stepper } from "@/components/ui/Stepper";
import { ArrowBackIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import type { AssetRenderSpec } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useDraftCampaign } from "@/features/campaign/wizard/useDraftCampaign";
import { WIZARD_TOTAL } from "@/features/campaign/wizard/wizardSteps";
import { AuthForm } from "./AuthForm";
import { useSessionStore } from "./sessionStore";

/**
 * Spec §11 — the account is only asked for once the user has seen their
 * concepts and picked one, and signing up continues straight into generation
 * instead of dropping the user on an empty dashboard.
 *
 * Returning users never see this screen: ConceptsStep starts generation
 * directly when a session already exists.
 */
export function SignupGate() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, loading } = useDraftCampaign();

  const session = useSessionStore((state) => state.session);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);
  const setSession = useSessionStore((state) => state.setSession);
  const started = useRef(false);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    if (loading || !detail) return;
    if (!detail.campaign.selected_concept_id) {
      router.replace("/create/concepts");
    }
  }, [loading, detail, router]);

  const startGeneration = useCallback(
    async (campaignId: string) => {
      await api.startGeneration(campaignId);
      track("generation_started", { campaign_id: campaignId });
      router.push(`/campaigns/${campaignId}`);
    },
    [router],
  );

  useEffect(() => {
    if (!sessionLoaded || loading || !detail || !session) return;
    if (!detail.campaign.selected_concept_id || started.current) return;
    started.current = true;
    void startGeneration(detail.campaign.id).catch((caught: unknown) => {
      started.current = false;
      toast(toPersianError(caught), "error");
    });
  }, [sessionLoaded, loading, detail, session, startGeneration, toast]);

  const selectedConcept = detail?.concepts.find((concept) => concept.selected);
  const primaryImage =
    detail?.product_images.find((image) => image.is_primary)?.storage_path ??
    detail?.product_images[0]?.storage_path ??
    null;

  const waitingForSession = !sessionLoaded || Boolean(session);

  return (
    <div className="min-h-dvh bg-ink-50">
      <header className="border-b border-ink-100 bg-white">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Link href="/create/concepts" aria-label="مرحله قبل">
              <Button variant="ghost" size="sm" className="size-11 p-0 sm:size-9">
                <ArrowBackIcon width={18} height={18} />
              </Button>
            </Link>
            <Logo className="text-base" />
            <span className="size-11 sm:size-9" aria-hidden="true" />
          </div>
          <div className="pb-3">
            <Stepper
              current={WIZARD_TOTAL}
              total={WIZARD_TOTAL}
              label="ساخت حساب"
            />
          </div>
        </Container>
      </header>

      <Container size="sm" className="flex flex-col gap-6 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-ink-900 sm:text-3xl">
            کمپینت آماده ساخته شدنه ✨
          </h1>
          <p className="mt-2 text-sm leading-7 text-ink-500">
            {waitingForSession
              ? "همه چیز آماده‌ست. داریم کمپین کاملت رو می‌سازیم."
              : "برای ساخت و ذخیره کمپین، حساب رایگان بساز."}
          </p>
        </div>

        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : selectedConcept ? (
          <Card className="flex items-center gap-4 p-4">
            <div className="w-24 shrink-0 overflow-hidden rounded-2xl">
              <AdCanvas
                spec={
                  {
                    template_id: "feed_classic",
                    background_id:
                      typeof selectedConcept.raw_json?.background_id === "string"
                        ? selectedConcept.raw_json.background_id
                        : "modern_ice",
                    headline_fa: selectedConcept.headline_fa,
                    subheadline_fa: null,
                    cta_fa: null,
                    price_text: null,
                    brand_name: null,
                    product_image_path: primaryImage,
                  } satisfies AssetRenderSpec
                }
                width={1080}
                height={1350}
              />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-brand-600">ایده انتخابی تو</p>
              <h2 className="mt-1 text-base font-bold text-ink-900">
                {selectedConcept.title_fa}
              </h2>
              <p className="mt-1 text-sm leading-7 text-ink-500">
                پست، استوری، کاروسل، کپشن‌ها و ایده ریلز ساخته می‌شه.
              </p>
            </div>
          </Card>
        ) : null}

        {waitingForSession ? (
          <Skeleton className="h-14 w-full" />
        ) : (
          <>
            <AuthForm
              submitLabel="ثبت‌نام و ساخت کمپین"
              verifyLabel="تأیید و ساخت کمپین"
              onRequestCode={() => track("signup_started", { provider: "email" })}
              onVerified={async (next) => {
                setSession(next);
                track("signup_completed", { provider: "email" });
                if (detail) await startGeneration(detail.campaign.id);
              }}
              onGoogle={async () => {
                if (!detail) return;
                track("signup_started", { provider: "google" });
                const redirect = new URL("/auth/callback", window.location.origin);
                redirect.searchParams.set("campaign", detail.campaign.id);
                await api.signInWithGoogle({ redirect_to: redirect.toString() });
                const current = await api.getSession();
                if (current) {
                  setSession(current);
                  track("signup_completed", { provider: "google" });
                  await startGeneration(detail.campaign.id);
                }
              }}
            />
            <p className="text-center text-xs leading-6 text-ink-400">
              اولین کمپین رایگانه و نیازی به کارت بانکی نیست.
            </p>
            <p className="text-center text-sm leading-7 text-ink-500">
              قبلاً حساب ساختی؟{" "}
              <Link href="/login" className="font-semibold text-brand-700">
                ورود
              </Link>
            </p>
          </>
        )}
      </Container>
    </div>
  );
}
