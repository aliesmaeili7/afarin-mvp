"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Feedback";
import { Stepper } from "@/components/ui/Stepper";
import { ArrowBackIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { AssetRenderSpec } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { productImagePath } from "@/features/campaign/productImagePath";
import { useDraftCampaign } from "@/features/campaign/wizard/useDraftCampaign";
import { WIZARD_TOTAL } from "@/features/campaign/wizard/wizardSteps";
import { AuthForm } from "./AuthForm";
import { useSessionStore } from "./sessionStore";

/**
 * Spec §11 — the account is only asked for once the user has seen their
 * directions and picked one, and signing up continues straight into generation
 * instead of dropping the user on an empty dashboard.
 *
 * Returning users never see this screen: DirectionsStep starts generation
 * directly when a session already exists.
 */
export function SignupGate() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
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
      router.replace("/create/directions");
      return;
    }
    if (!detail.campaign.visual_creation_mode) {
      router.replace("/create/directions");
      return;
    }
    if (
      detail.campaign.visual_creation_mode === "creative" &&
      !(detail.campaign.visual_recipe_json as { style_id?: string } | undefined)
        ?.style_id
    ) {
      router.replace("/create/directions");
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
    if (!detail.campaign.visual_creation_mode) return;
    if (
      detail.campaign.visual_creation_mode === "creative" &&
      !(detail.campaign.visual_recipe_json as { style_id?: string } | undefined)
        ?.style_id
    ) {
      return;
    }
    started.current = true;
    void startGeneration(detail.campaign.id).catch((caught: unknown) => {
      started.current = false;
      toast(displayError(caught), "error");
    });
  }, [sessionLoaded, loading, detail, session, startGeneration, toast, displayError]);

  const selectedConcept = detail?.concepts.find((concept) => concept.selected);
  const primary =
    detail?.product_images.find((image) => image.is_primary) ??
    detail?.product_images[0] ??
    null;
  const primaryImage = productImagePath(primary);

  const waitingForSession = !sessionLoaded || Boolean(session);

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Link href="/create/directions" aria-label={t("common.previousStep")}>
              <Button variant="ghost" size="sm" className="size-11 p-0 sm:size-9">
                <ArrowBackIcon width={18} height={18} />
              </Button>
            </Link>
            <Logo className="text-base" />
            <PreferencesTrigger />
          </div>
          <div className="pb-3">
            <Stepper
              current={WIZARD_TOTAL}
              total={WIZARD_TOTAL}
              label={t("auth.signupStep")}
            />
          </div>
        </Container>
      </header>

      <Container size="sm" className="flex flex-col gap-6 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-foreground sm:text-3xl">
            {t("auth.signupTitle")}
          </h1>
          <p className="mt-2 text-sm leading-7 text-muted">
            {waitingForSession ? t("auth.signupReady") : t("auth.signupNeedAccount")}
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
              <p className="text-xs font-semibold text-brand-600">{t("auth.selectedIdea")}</p>
              <h2 className="mt-1 text-base font-bold text-foreground">
                {selectedConcept.title_fa}
              </h2>
              <p className="mt-1 text-sm leading-7 text-muted">{t("auth.signupPreview")}</p>
            </div>
          </Card>
        ) : null}

        {waitingForSession ? (
          <Skeleton className="h-14 w-full" />
        ) : (
          <>
            <AuthForm
              mode="signup"
              submitLabel={t("auth.submitSignup")}
              verifyLabel={t("auth.verifySignup")}
              onEmailStart={() => track("signup_started", { provider: "email" })}
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
              {t("auth.firstFree")}
            </p>
            <p className="text-center text-sm leading-7 text-muted">
              {t("auth.hasAccount")}{" "}
              <Link href="/login" className="font-semibold text-brand-700">
                {t("nav.login")}
              </Link>
            </p>
          </>
        )}
      </Container>
    </div>
  );
}
