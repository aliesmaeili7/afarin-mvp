"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Badge, Card } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { ImageIcon, PlusIcon, SparkleIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { formatRelativeDay } from "@/lib/format/persian";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import type { Brand, CampaignStatus, CampaignSummary } from "@/types/domain";
import { AdCanvas } from "@/features/campaign/ad-renderer/AdCanvas";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import { useSessionStore } from "@/features/auth/sessionStore";
import { beginNewCampaign } from "@/features/campaign/wizard/useWizardStore";

const STATUS_LABELS: Record<CampaignStatus, { label: string; tone: "neutral" | "brand" | "success" | "warning" | "danger" }> = {
  draft: { label: "ناتمام", tone: "neutral" },
  brief_complete: { label: "ناتمام", tone: "neutral" },
  concepts_ready: { label: "انتخاب ایده", tone: "brand" },
  concept_selected: { label: "آماده ساخت", tone: "brand" },
  queued: { label: "در صف", tone: "warning" },
  generating: { label: "در حال ساخت", tone: "warning" },
  ready: { label: "آماده", tone: "success" },
  partial_failed: { label: "ناقص", tone: "warning" },
  failed: { label: "ناموفق", tone: "danger" },
};

export function DashboardPage() {
  const router = useRouter();
  const { toast } = useToast();

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
      toast(toPersianError(caught), "error");
      setCreating(null);
    }
  }

  if (!sessionLoaded) {
    return (
      <div className="min-h-dvh bg-ink-50">
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
      <div className="min-h-dvh bg-ink-50">
        <SiteHeader />
        <Container size="sm" className="py-16">
          <EmptyState
            icon={<SparkleIcon />}
            title="هنوز وارد نشدی"
            description="با ساخت اولین کمپین، حساب رایگانت ساخته می‌شه و کمپین‌هات اینجا ذخیره می‌مونه."
            action={
              <Link href="/create">
                <Button>ساخت کمپین رایگان</Button>
              </Link>
            }
          />
        </Container>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-ink-50">
      <SiteHeader />

      <Container size="lg" className="flex flex-col gap-10 py-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {/* No greeting by name: the mock account only knows an email
                address, and a Latin local-part reads badly in a Persian UI. */}
            <h1 className="text-2xl font-extrabold text-ink-900">سلام 👋</h1>
            <p className="mt-1 text-sm leading-7 text-ink-500">
              کمپین بعدی‌ات رو بساز یا کمپین‌های قبلی رو ببین.
            </p>
          </div>
          <Button
            size="lg"
            loading={creating === "new"}
            onClick={() => startCampaign(null)}
            iconStart={<PlusIcon width={18} height={18} />}
          >
            کمپین جدید بساز
          </Button>
        </header>

        <section>
          <h2 className="mb-4 text-lg font-extrabold text-ink-900">
            کمپین‌های اخیر
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
              title="هنوز کمپینی نساختی"
              description="اولین کمپینت رایگانه."
              action={
                <Button onClick={() => startCampaign(null)}>ساخت کمپین</Button>
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
          <h2 className="mb-4 text-lg font-extrabold text-ink-900">برندهای من</h2>
          {!sessionLoaded || brands.loading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : (brands.data ?? []).length === 0 ? (
            <EmptyState
              title="هنوز برندی ذخیره نکردی"
              description="بعد از ساخت اولین کمپین می‌تونی اطلاعات برندت رو ذخیره کنی."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(brands.data ?? []).map((brand) => (
                <Card key={brand.id} className="flex flex-col gap-3 p-5">
                  <div>
                    <h3 className="text-base font-bold text-ink-900">{brand.name}</h3>
                    <p className="mt-1 line-clamp-2 text-sm leading-7 text-ink-500">
                      {brand.description ?? "بدون توضیح"}
                    </p>
                  </div>
                  <div className="mt-auto flex gap-2">
                    <Link href={`/brands/${brand.id}`} className="flex-1">
                      <Button variant="outline" size="sm" fullWidth>
                        ویرایش برند
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      className="flex-1"
                      loading={creating === brand.id}
                      onClick={() => startCampaign(brand.id)}
                    >
                      کمپین جدید
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
  const photoUrl = useResolvedAssetUrl(
    campaign.thumbnail_spec ? null : campaign.thumbnail_path,
  );
  const status = STATUS_LABELS[campaign.status];
  const subtitle = [campaign.brand_name, formatRelativeDay(campaign.created_at)]
    .filter(Boolean)
    .join(" · ");

  return (
    <Link href={`/campaigns/${campaign.id}`} className="group block">
      <Card className="flex gap-3 overflow-hidden p-3 transition-shadow group-hover:shadow-lift">
        <div className="grid w-24 shrink-0 place-items-center overflow-hidden rounded-2xl bg-ink-100 text-ink-300">
          {campaign.thumbnail_spec ? (
            <AdCanvas
              spec={campaign.thumbnail_spec}
              storagePath={campaign.thumbnail_path}
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
            <h3 className="min-w-0 flex-1 truncate text-sm font-bold text-ink-900">
              {campaign.product_name ?? "کمپین بدون نام"}
            </h3>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
          <p className="mt-1 truncate text-xs text-ink-400">{subtitle}</p>
          <span className="mt-auto pt-2 text-sm font-semibold text-brand-700 underline-offset-4 group-hover:underline">
            مشاهده
          </span>
        </div>
      </Card>
    </Link>
  );
}
