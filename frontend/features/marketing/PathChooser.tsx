"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/layout/Container";
import { ArrowForwardIcon } from "@/components/ui/icons";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

/**
 * The two content paths, given equal weight.
 *
 * Afarin is no longer only an advertising tool, so the homepage asks what the
 * visitor is making rather than assuming a product photo.
 */
export const AD_CREATE_HREF = "/create";
export const EDUCATION_CREATE_HREF = "/create/education";
export function PathChooser() {
  const { t } = useI18n();
  const paths = [
    {
      href: AD_CREATE_HREF,
      emoji: "🛍",
      title: t("landing.pathAd"),
      body: t("landing.pathAdBody"),
      cta: t("landing.pathAdCta"),
    },
    {
      href: EDUCATION_CREATE_HREF,
      emoji: "📚",
      title: t("landing.pathEdu"),
      body: t("landing.pathEduBody"),
      cta: t("landing.pathEduCta"),
    },
  ];

  return (
    <section className="py-12 sm:py-16" data-path-chooser>
      <Container size="md">
        <h2 className="text-center text-2xl font-extrabold text-foreground">
          {t("landing.pathTitle")}
        </h2>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {paths.map((path) => (
            <Card key={path.href} className="flex flex-col gap-3 p-6">
              <span className="text-3xl" aria-hidden="true">
                {path.emoji}
              </span>
              <h3 className="text-lg font-bold text-foreground">{path.title}</h3>
              <p className="flex-1 text-sm leading-7 text-muted">{path.body}</p>
              <Link href={path.href}>
                <Button
                  fullWidth
                  variant="subtle"
                  iconEnd={<ArrowForwardIcon width={18} height={18} />}
                >
                  {path.cta}
                </Button>
              </Link>
            </Card>
          ))}
        </div>
      </Container>
    </section>
  );
}
