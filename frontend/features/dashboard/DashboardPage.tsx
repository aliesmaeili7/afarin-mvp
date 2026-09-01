"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Badge, Card } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { ImageIcon, PlusIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { formatRelativeDay } from "@/lib/format/display";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
import type { Brand, CampaignStatus, CampaignSummary, EducationalPostSummary } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import { useSessionStore } from "@/features/auth/sessionStore";
import { beginNewCampaign } from "@/features/campaign/wizard/useWizardStore";

const STATUS_TONES: Record<
  CampaignStatus,
  "neutral" | "brand" | "success" | "warning" | "danger"
> = {
  draft: "neutral",
  brief_complete: "neutral",
  concepts_ready: "brand",
  concept_selected: "brand",
  candidates_ready: "brand",
  queued: "warning",
  generating: "warning",
  ready: "success",
  partial_failed: "warning",
  failed: "danger",
};

export function DashboardPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();

  const session = useSessionStore((state) => state.session);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);

  const [creating, setCreating] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  const campaigns = useAsyncData<CampaignSummary[]>(
    async () => {
      // Wait until we know whether a Supabase session exists. Listing before
      // that uses the spent anonymous cookie and returns an empty history.
      if (!sessionLoaded) return [];
      return api.listCampaigns();
    },
    [sessionLoaded, session?.user.id],
  );
  const educationalPosts = useAsyncData<EducationalPostSummary[]>(
    async () => {
      if (!sessionLoaded || !session) return [];
      return api.listEducationalPosts();
    },
    [sessionLoaded, session?.user.id],
  );
  const brands = useAsyncData<Brand[]>(
    async () => {
      if (!sessionLoaded) return [];
      return api.listBrands();
    },
    [sessionLoaded, session?.user.id],
  );

  async function startCampaign(brandId: string | null) {
    setCreating(brandId ?? "new");
    try {
      await beginNewCampaign(brandId);
      track("campaign_repeated", { brand_id: brandId });
      router.push("/create");
    } catch (caught) {
      toast(displayError(caught), "error");
      setCreating(null);
    }
  }

  if (!sessionLoaded) {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="lg" className="flex flex-col gap-4 py-8">
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </Container>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-dvh bg-background">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <EmptyState
            icon={<SparkleIcon />}
            title={t("dashboard.loggedOutTitle")}
            description={t("dashboard.loggedOutDescription")}
            action={
              <Link href="/">
                <Button>{t("nav.startFree")}</Button>
              </Link>
            }
          />
        </Container>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-background">
      <SiteHeader />

      <Container size="lg" className="flex flex-col gap-10 py-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {/* No greeting by name: the mock account only knows an email
                address, and a Latin local-part reads badly in a Persian UI. */}
            <h1 className="text-2xl font-extrabold text-foreground">{t("dashboard.hello")}</h1>
            <p className="mt-1 text-sm leading-7 text-muted">{t("dashboard.subtitle")}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Link href="/create/education">
              <Button
                size="lg"
                variant="outline"
                iconStart={<PlusIcon width={18} height={18} />}
              >
                {t("dashboard.createEducation")}
              </Button>
            </Link>
            <Button
              size="lg"
              loading={creating === "new"}
              onClick={() => startCampaign(null)}
              iconStart={<PlusIcon width={18} height={18} />}
            >
              {t("dashboard.create")}
            </Button>
          </div>
        </header>

        <section>
          <h2 className="mb-4 text-lg font-extrabold text-foreground">
            {t("dashboard.recent")}
          </h2>
          {!sessionLoaded || campaigns.loading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
          ) : (campaigns.data ?? []).length === 0 ? (
            <EmptyState
              icon={<ImageIcon />}
              title={t("dashboard.emptyTitle")}
              description={t("dashboard.emptyDescription")}
              action={
                <Button onClick={() => startCampaign(null)}>{t("dashboard.emptyAction")}</Button>
              }
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(campaigns.data ?? []).map((campaign) => (
                <CampaignCard key={campaign.id} campaign={campaign} />
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-4 text-lg font-extrabold text-foreground">
            {t("education.myPosts")}
          </h2>
          {!sessionLoaded || educationalPosts.loading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
          ) : (educationalPosts.data ?? []).length === 0 ? (
            <EmptyState
              icon={<ImageIcon />}
              title={t("dashboard.educationEmptyTitle")}
              description={t("education.empty")}
              action={
                <Link href="/create/education">
                  <Button>{t("dashboard.educationEmptyAction")}</Button>
                </Link>
              }
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(educationalPosts.data ?? []).map((post) => (
                <EducationCard key={post.id} post={post} />
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-4 text-lg font-extrabold text-foreground">{t("dashboard.brands")}</h2>
          {!sessionLoaded || brands.loading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : (brands.data ?? []).length === 0 ? (
            <EmptyState
              title={t("dashboard.brandsEmptyTitle")}
              description={t("dashboard.brandsEmptyDescription")}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(brands.data ?? []).map((brand) => (
                <Card key={brand.id} className="flex flex-col gap-3 p-5">
                  <div>
                    <h3 className="text-base font-bold text-foreground">{brand.name}</h3>
                    <p className="mt-1 line-clamp-2 text-sm leading-7 text-muted">
                      {brand.description ?? t("common.noDescription")}
                    </p>
                  </div>
                  <div className="mt-auto flex gap-2">
                    <Link href={`/brands/${brand.id}`} className="flex-1">
                      <Button variant="outline" size="sm" fullWidth>
                        {t("dashboard.editBrand")}
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      className="flex-1"
                      loading={creating === brand.id}
                      onClick={() => startCampaign(brand.id)}
                    >
                      {t("nav.newCampaign")}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </Container>
    </div>
  );
}

function CampaignCard({ campaign }: { campaign: CampaignSummary }) {
  const { t, locale } = useI18n();
  const photoUrl = useResolvedAssetUrl(
    campaign.thumbnail_spec ? null : campaign.thumbnail_path,
  );
  const subtitle = [campaign.brand_name, formatRelativeDay(campaign.created_at, locale)]
    .filter(Boolean)
    .join(" · ");

  return (
    <Link href={`/campaigns/${campaign.id}`} className="group block">
      <Card className="flex gap-3 overflow-hidden p-3 transition-shadow group-hover:shadow-lift">
        <div className="grid w-24 shrink-0 place-items-center overflow-hidden rounded-2xl bg-ink-100 text-ink-300">
          {campaign.thumbnail_spec ? (
            <AdCanvas
              spec={campaign.thumbnail_spec}
              width={1080}
              height={1350}
            />
          ) : photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={photoUrl}
              alt=""
              className="h-20 w-full object-contain p-1"
            />
          ) : (
            <span className="grid h-20 w-full place-items-center">
              <ImageIcon />
            </span>
          )}
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-2">
            <h3 className="min-w-0 flex-1 truncate text-sm font-bold text-foreground">
              {campaign.product_name ?? t("common.untitledCampaign")}
            </h3>
            <Badge tone={STATUS_TONES[campaign.status]}>
              {t(`campaign.status.${campaign.status}` as TranslationKey)}
            </Badge>
          </div>
          <p className="mt-1 truncate text-xs text-ink-400">{subtitle}</p>
          <span className="mt-auto pt-2 text-sm font-semibold text-brand-700 underline-offset-4 group-hover:underline">
            {t("common.view")}
          </span>
        </div>
      </Card>
    </Link>
  );
}

const EDUCATION_STATUS_TONES: Record<
  EducationalPostSummary["status"],
  "neutral" | "brand" | "success" | "warning" | "danger"
> = {
  queued: "warning",
  generating: "warning",
  ready: "success",
  failed: "danger",
};

function EducationCard({ post }: { post: EducationalPostSummary }) {
  const { t, locale } = useI18n();
  const photoUrl = useResolvedAssetUrl(post.image_storage_path);
  const subtitle = formatRelativeDay(post.created_at, locale);

  return (
    <Link href={`/education/${post.id}`} className="group block">
      <Card className="flex gap-3 overflow-hidden p-3 transition-shadow group-hover:shadow-lift">
        <div className="grid w-24 shrink-0 place-items-center overflow-hidden rounded-2xl bg-ink-100 text-ink-300">
          {photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photoUrl} alt="" className="h-20 w-full object-cover" />
          ) : (
            <span className="grid h-20 w-full place-items-center">
              <ImageIcon />
            </span>
          )}
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-2">
            <h3 className="min-w-0 flex-1 truncate text-sm font-bold text-foreground">
              {post.headline ?? t("education.themeUnnamed")}
            </h3>
            <Badge tone={EDUCATION_STATUS_TONES[post.status]}>
              {t(`campaign.status.${post.status}` as TranslationKey)}
            </Badge>
          </div>
          <p className="mt-1 truncate text-xs text-ink-400">{subtitle}</p>
          <span className="mt-auto pt-2 text-sm font-semibold text-brand-700 underline-offset-4 group-hover:underline">
            {t("common.view")}
          </span>
        </div>
      </Card>
    </Link>
  );
}
