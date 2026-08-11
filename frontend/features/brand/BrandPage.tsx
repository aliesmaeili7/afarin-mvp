"use client";

import Link from "next/link";
import { useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { Container } from "@/components/layout/Container";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Field";
import { ChoiceCard } from "@/components/ui/ChoiceCard";
import { useToast } from "@/components/ui/Toast";
import { VISUAL_STYLES } from "@/lib/content/styles";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useHydratedForm } from "@/lib/hooks/useHydratedForm";
import type { Brand, VisualStyle } from "@/types/domain";

interface BrandForm {
  name: string;
  description: string;
  category: string;
  instagram_handle: string;
  website: string;
  target_audience: string;
  tone: string;
  visual_style: VisualStyle | null;
}

/** Spec §18 — a simple, fully editable Brand Kit. */
export function BrandPage({ brandId }: { brandId: string }) {
  const { toast } = useToast();
  const { data, loading, error, reload } = useAsyncData<Brand>(
    () => api.getBrand(brandId),
    [brandId],
  );

  const [form, setForm] = useHydratedForm<BrandForm | null>(
    data?.id ?? null,
    () =>
      data
        ? {
            name: data.name,
            description: data.description ?? "",
            category: data.category ?? "",
            instagram_handle: data.instagram_handle ?? "",
            website: data.website ?? "",
            target_audience: data.target_audience ?? "",
            tone: data.tone ?? "",
            visual_style: data.visual_style,
          }
        : null,
    null,
  );
  const [saving, setSaving] = useState(false);

  function update<K extends keyof BrandForm>(key: K, value: BrandForm[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  async function handleSave() {
    if (!form) return;
    setSaving(true);
    try {
      await api.updateBrand(brandId, {
        name: form.name,
        description: form.description || null,
        category: form.category || null,
        instagram_handle: form.instagram_handle || null,
        website: form.website || null,
        target_audience: form.target_audience || null,
        tone: form.tone || null,
        visual_style: form.visual_style,
      });
      await reload();
      toast("اطلاعات برند ذخیره شد");
    } catch (caught) {
      toast(toPersianError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-dvh bg-ink-50">
      <SiteHeader />

      <Container size="md" className="flex flex-col gap-6 py-8">
        {loading && !form ? (
          <>
            <Skeleton className="h-10 w-1/2" />
            <Skeleton className="h-96 w-full" />
          </>
        ) : error || !form ? (
          <ErrorState
            title="این برند پیدا نشد"
            description={error ?? undefined}
            action={
              <Link href="/dashboard">
                <Button>بازگشت به داشبورد</Button>
              </Link>
            }
          />
        ) : (
          <>
            <header>
              <h1 className="text-2xl font-extrabold text-ink-900">
                هویت برند {form.name}
              </h1>
              <p className="mt-1 text-sm leading-7 text-ink-500">
                این اطلاعات توی کمپین‌های بعدی به‌صورت خودکار استفاده می‌شه.
              </p>
            </header>

            <Card>
              <CardHeader title="اطلاعات پایه" />
              <div className="flex flex-col gap-5 p-5">
                <TextField
                  label="اسم برند"
                  value={form.name}
                  onChange={(event) => update("name", event.target.value)}
                />
                <TextAreaField
                  label="معرفی کسب‌وکار"
                  optional
                  value={form.description}
                  onChange={(event) => update("description", event.target.value)}
                />
                <TextField
                  label="دسته‌بندی"
                  optional
                  placeholder="مثلاً پوشاک، مواد غذایی، آرایشی"
                  value={form.category}
                  onChange={(event) => update("category", event.target.value)}
                />
                <TextField
                  label="آیدی اینستاگرام"
                  optional
                  dir="ltr"
                  placeholder="yourshop"
                  value={form.instagram_handle}
                  onChange={(event) =>
                    update("instagram_handle", event.target.value)
                  }
                />
                <TextField
                  label="وب‌سایت"
                  optional
                  type="url"
                  placeholder="https://example.com"
                  value={form.website}
                  onChange={(event) => update("website", event.target.value)}
                />
              </div>
            </Card>

            <Card>
              <CardHeader title="لحن و مخاطب" />
              <div className="flex flex-col gap-5 p-5">
                <TextField
                  label="مخاطب هدف"
                  optional
                  value={form.target_audience}
                  onChange={(event) =>
                    update("target_audience", event.target.value)
                  }
                />
                <TextField
                  label="لحن مورد علاقه"
                  optional
                  placeholder="مثلاً صمیمی و ساده"
                  value={form.tone}
                  onChange={(event) => update("tone", event.target.value)}
                />
              </div>
            </Card>

            <Card>
              <CardHeader
                title="سبک بصری پیش‌فرض"
                description="کمپین‌های بعدی با این سبک شروع می‌شن."
              />
              <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-3">
                {VISUAL_STYLES.map((option) => (
                  <ChoiceCard
                    key={option.value}
                    selected={form.visual_style === option.value}
                    onSelect={() => update("visual_style", option.value)}
                    title={option.label_fa}
                    media={
                      <span
                        className="block h-14"
                        style={{ background: option.preview_css }}
                        aria-hidden="true"
                      />
                    }
                  />
                ))}
              </div>
            </Card>

            <div className="sticky bottom-4 flex gap-2">
              <Button
                size="lg"
                fullWidth
                loading={saving}
                onClick={handleSave}
                className="shadow-lift"
              >
                ذخیره تغییرات
              </Button>
            </div>
          </>
        )}
      </Container>
    </div>
  );
}
