"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Feedback";
import { TextField } from "@/components/ui/Field";
import { Stepper } from "@/components/ui/Stepper";
import { ArrowBackIcon, GoogleIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import type { AssetRenderSpec } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useDraftCampaign } from "@/features/campaign/wizard/useDraftCampaign";
import { WIZARD_TOTAL } from "@/features/campaign/wizard/wizardSteps";
import { useSessionStore } from "./sessionStore";

/**
 * Spec §11 — the account is only asked for once the user has seen their
 * concepts and picked one, and signing up continues straight into generation
 * instead of dropping the user on an empty dashboard.
 */
export function SignupGate() {
  const router = useRouter();
  const { toast } = useToast();
  const { detail, loading } = useDraftCampaign();

  const session = useSessionStore((state) => state.session);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);
  const setSession = useSessionStore((state) => state.setSession);

  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    if (loading || !detail) return;
    if (!detail.campaign.selected_concept_id) {
      router.replace("/create/concepts");
    }
  }, [loading, detail, router]);

  const selectedConcept = detail?.concepts.find((concept) => concept.selected);
  const primaryImage =
    detail?.product_images.find((image) => image.is_primary)?.storage_path ??
    detail?.product_images[0]?.storage_path ??
    null;

  async function startGeneration(campaignId: string) {
    await api.startGeneration(campaignId);
    track("generation_started", { campaign_id: campaignId });
    router.push(`/campaigns/${campaignId}`);
  }

  async function handleSignUp(provider: "email" | "google") {
    if (!detail) return;

    const address =
      provider === "google" ? "user@gmail.com" : email.trim().toLowerCase();

    if (provider === "email" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(address)) {
      setEmailError("ایمیل معتبر وارد کن.");
      return;
    }

    setSubmitting(true);
    track("signup_started", { provider });
    try {
      const newSession = await api.signUp({ email: address, provider });
      setSession(newSession);
      track("signup_completed", { provider });
      await startGeneration(detail.campaign.id);
    } catch (caught) {
      toast(toPersianError(caught), "error");
      setSubmitting(false);
    }
  }

  async function handleGenerateAsMember() {
    if (!detail) return;
    setSubmitting(true);
    try {
      await startGeneration(detail.campaign.id);
    } catch (caught) {
      toast(toPersianError(caught), "error");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-dvh bg-ink-50">
      {/* Keeps the wizard's chrome so the user can still go back and change
          their concept, and can see how far along they are. */}
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
            {session
              ? "همه چیز آماده‌ست. با یک کلیک کمپین کاملت رو می‌سازیم."
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

        {session ? (
          <Button
            size="lg"
            fullWidth
            loading={submitting}
            onClick={handleGenerateAsMember}
            iconStart={<SparkleIcon width={18} height={18} />}
          >
            ساخت کمپین
          </Button>
        ) : (
          <Card className="flex flex-col gap-4 p-5">
            <Button
              variant="outline"
              size="lg"
              fullWidth
              disabled={submitting}
              onClick={() => handleSignUp("google")}
              iconStart={<GoogleIcon />}
            >
              ادامه با گوگل
            </Button>

            <div className="flex items-center gap-3 text-xs text-ink-400">
              <span className="h-px flex-1 bg-ink-200" />
              یا
              <span className="h-px flex-1 bg-ink-200" />
            </div>

            <TextField
              label="ایمیل"
              type="email"
              inputMode="email"
              placeholder="you@example.com"
              value={email}
              error={emailError}
              onChange={(event) => {
                setEmail(event.target.value);
                setEmailError(null);
              }}
            />

            <Button
              size="lg"
              fullWidth
              loading={submitting}
              onClick={() => handleSignUp("email")}
              iconStart={<SparkleIcon width={18} height={18} />}
            >
              ثبت‌نام و ساخت کمپین
            </Button>

            <p className="text-center text-xs leading-6 text-ink-400">
              اولین کمپین رایگانه و نیازی به کارت بانکی نیست.
            </p>
          </Card>
        )}
      </Container>
    </div>
  );
}
