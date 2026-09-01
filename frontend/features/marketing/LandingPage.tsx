"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ArrowForwardIcon } from "@/components/ui/icons";
import { track } from "@/lib/analytics/track";
import { CATEGORY_EXAMPLES, HERO_EXAMPLE } from "@/lib/content/landingExamples";
import { formatDigits } from "@/lib/format/display";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { BeforeAfter } from "./BeforeAfter";
import { PathChooser } from "./PathChooser";

const CATEGORY_KEYS: Record<string, TranslationKey> = {
  saffron: "landing.categoryFood",
  perfume: "landing.categoryBeauty",
  clothing: "landing.categoryClothing",
  coffee: "landing.categoryPackaged",
};

export function LandingPage() {
  const { t, locale } = useI18n();

  useEffect(() => {
    track("landing_viewed");
  }, []);

  const how = [
    { title: t("landing.how1Title"), description: t("landing.how1Body") },
    { title: t("landing.how2Title"), description: t("landing.how2Body") },
    { title: t("landing.how3Title"), description: t("landing.how3Body") },
  ];
  const deliverables = [
    { title: t("landing.deliverFeed"), emoji: "🖼", description: t("landing.deliverFeedBody") },
    { title: t("landing.deliverStory"), emoji: "📱", description: t("landing.deliverStoryBody") },
    { title: t("landing.deliverCarousel"), emoji: "🎞", description: t("landing.deliverCarouselBody") },
    { title: t("landing.deliverCaption"), emoji: "✍️", description: t("landing.deliverCaptionBody") },
    { title: t("landing.deliverReel"), emoji: "🎬", description: t("landing.deliverReelBody") },
  ];

  return (
    <div className="min-h-dvh bg-background">
      <SiteHeader />

      <main>
        <section className="relative overflow-hidden">
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-96"
            style={{
              background:
                "radial-gradient(80% 60% at 70% 0%, rgba(124,58,237,0.16) 0%, transparent 70%)",
            }}
            aria-hidden="true"
          />
          <Container size="lg" className="relative py-10 sm:py-16">
            <div className="grid items-center gap-10 lg:grid-cols-[1fr_1.05fr]">
              <div className="animate-fade-up text-center lg:text-start">
                <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-surface px-3 py-1.5 text-xs font-semibold text-brand-700">
                  ✨ {t("landing.badge")}
                </span>

                <h1 className="mt-5 text-3xl font-extrabold leading-[1.5] text-foreground sm:text-4xl lg:text-5xl">
                  {t("landing.heroBefore")}{" "}
                  <span className="text-gradient">{t("landing.heroHighlight")}</span>
                  {t("landing.heroAfter") ? ` ${t("landing.heroAfter")}` : ""}
                </h1>

                <p className="mx-auto mt-4 max-w-md text-base leading-8 text-muted lg:mx-0">
                  {t("landing.subtitle")}
                </p>

                <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
                  <Link href="/create" className="w-full sm:w-auto">
                    <Button
                      size="lg"
                      fullWidth
                      iconEnd={<ArrowForwardIcon width={18} height={18} />}
                    >
                      {t("landing.pathAdCta")}
                    </Button>
                  </Link>
                  <Link href="/create/education" className="w-full sm:w-auto">
                    <Button size="lg" variant="outline" fullWidth>
                      {t("landing.pathEduCta")}
                    </Button>
                  </Link>
                </div>
                <p className="mt-3 text-xs text-muted">{t("landing.noCard")}</p>
              </div>

              <div className="animate-fade-up">
                <BeforeAfter example={HERO_EXAMPLE} />
                <p className="mt-4 text-center text-xs text-muted">
                  {t("landing.afterCaption")}
                </p>
              </div>
            </div>
          </Container>
        </section>

        <PathChooser />

        <section className="py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-foreground">
              {t("landing.forAnyBusiness")}
            </h2>
            <p className="mt-2 text-center text-sm leading-7 text-muted">
              {t("landing.samples")}
            </p>

            <div className="mt-8 grid gap-5 sm:grid-cols-3">
              {CATEGORY_EXAMPLES.map((example) => (
                <div key={example.id} className="flex flex-col gap-3">
                  <div className="overflow-hidden rounded-3xl shadow-soft">
                    <AdCanvas spec={example.spec} width={1080} height={1350} />
                  </div>
                  <span className="text-center text-sm font-semibold text-muted">
                    {t(CATEGORY_KEYS[example.id] ?? "landing.categoryFood")}
                  </span>
                </div>
              ))}
            </div>
          </Container>
        </section>

        <section className="bg-surface py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-foreground">
              {t("landing.howTitle")}
            </h2>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {how.map((step, index) => (
                <Card key={step.title} className="p-5">
                  <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-sm font-extrabold text-brand-700">
                    {formatDigits(index + 1, locale)}
                  </span>
                  <h3 className="mt-4 text-base font-bold text-foreground">{step.title}</h3>
                  <p className="mt-1 text-sm leading-7 text-muted">{step.description}</p>
                </Card>
              ))}
            </div>
          </Container>
        </section>

        <section className="py-12 sm:py-16">
          <Container size="lg">
            <h2 className="text-center text-2xl font-extrabold text-foreground">
              {t("landing.deliverTitle")}
            </h2>

            <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {deliverables.map((item) => (
                <Card key={item.title} className="p-4 text-center">
                  <span className="text-2xl" aria-hidden="true">
                    {item.emoji}
                  </span>
                  <h3 className="mt-2 text-sm font-bold text-foreground">{item.title}</h3>
                  <p className="mt-1 text-xs leading-6 text-muted">{item.description}</p>
                </Card>
              ))}
            </div>
          </Container>
        </section>

        <section className="pb-16">
          <Container size="md">
            <div className="rounded-[2rem] bg-gradient-to-bl from-brand-700 via-brand-600 to-coral-500 p-8 text-center text-white shadow-lift sm:p-12">
              <h2 className="text-2xl font-extrabold sm:text-3xl">{t("landing.ctaTitle")}</h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-8 text-white/85">
                {t("landing.ctaBody")}
              </p>
              <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Link href="/create">
                  <Button size="lg" variant="outline" className="bg-white text-ink-900">
                    {t("landing.pathAdCta")}
                  </Button>
                </Link>
                <Link href="/create/education">
                  <Button size="lg" variant="outline" className="bg-white text-ink-900">
                    {t("landing.pathEduCta")}
                  </Button>
                </Link>
              </div>
            </div>
          </Container>
        </section>
      </main>

      <footer className="border-t border-border bg-surface py-8">
        <Container size="lg" className="flex flex-col items-center gap-3 text-center">
          <Logo />
          <p className="text-xs leading-6 text-muted">{t("landing.footer")}</p>
        </Container>
      </footer>
    </div>
  );
}
