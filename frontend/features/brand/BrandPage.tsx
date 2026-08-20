"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
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
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { TranslationKey } from "@/lib/i18n/t";
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
  const { t } = useI18n();
  const displayError = useDisplayError();
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
      toast(t("brand.saved"));
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background">
      <SiteHeader />

      <Container size="md" className="flex flex-col gap-6 py-8">
        {loading && !form ? (
          <>
            <Skeleton className="h-10 w-1/2" />
            <Skeleton className="h-96 w-full" />
          </>
        ) : error || !form ? (
          <ErrorState
            title={t("errors.brandNotFound")}
            description={error ?? undefined}
            action={
              <Link href="/dashboard">
                <Button>{t("brand.backDashboard")}</Button>
              </Link>
            }
          />
        ) : (
          <>
            <header>
              <h1 className="text-2xl font-extrabold text-foreground">
                {t("brand.title", { name: form.name })}
              </h1>
              <p className="mt-1 text-sm leading-7 text-muted">{t("brand.subtitle")}</p>
            </header>

            <Card>
              <CardHeader title={t("brand.basics")} />
              <div className="flex flex-col gap-5 p-5">
                <TextField
                  label={t("brand.name")}
                  value={form.name}
                  onChange={(event) => update("name", event.target.value)}
                />
                <TextAreaField
                  label={t("brand.about")}
                  optional
                  value={form.description}
                  onChange={(event) => update("description", event.target.value)}
                />
                <TextField
                  label={t("brand.category")}
                  optional
                  placeholder={t("brand.categoryPlaceholder")}
                  value={form.category}
                  onChange={(event) => update("category", event.target.value)}
                />
                <TextField
                  label={t("brand.instagram")}
                  optional
                  dir="ltr"
                  placeholder="yourshop"
                  value={form.instagram_handle}
                  onChange={(event) =>
                    update("instagram_handle", event.target.value)
                  }
                />
                <TextField
                  label={t("brand.website")}
                  optional
                  type="url"
                  placeholder="https://example.com"
                  value={form.website}
                  onChange={(event) => update("website", event.target.value)}
                />
              </div>
            </Card>

            <Card>
              <CardHeader title={t("brand.toneAudience")} />
              <div className="flex flex-col gap-5 p-5">
                <TextField
                  label={t("brand.audience")}
                  optional
                  value={form.target_audience}
                  onChange={(event) =>
                    update("target_audience", event.target.value)
                  }
                />
                <TextField
                  label={t("brand.tone")}
                  optional
                  placeholder={t("brand.tonePlaceholder")}
                  value={form.tone}
                  onChange={(event) => update("tone", event.target.value)}
                />
              </div>
            </Card>

            <Card>
              <CardHeader
                title={t("brand.defaultStyle")}
                description={t("brand.defaultStyleHint")}
              />
              <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-3">
                {VISUAL_STYLES.map((option) => (
                  <ChoiceCard
                    key={option.value}
                    selected={form.visual_style === option.value}
                    onSelect={() => update("visual_style", option.value)}
                    title={t(`campaign.style.${option.value}.label` as TranslationKey)}
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
                {t("brand.save")}
              </Button>
            </div>
          </>
        )}
      </Container>
    </div>
  );
}
