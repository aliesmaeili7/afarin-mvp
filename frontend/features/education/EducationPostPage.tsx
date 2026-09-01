"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { ArrowBackIcon, DownloadIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { EducationalPost } from "@/types/domain";
import { useResolvedAssetUrl } from "@/features/campaign/ad-renderer/useResolvedAssetUrl";
import {
  canSaveGeneratedTheme,
  themeLabel,
} from "./educationPost";
import { EducationProgress } from "./EducationProgress";
import { useEducationalPost } from "./useEducationalPost";

export function EducationPostPage({ postId }: { postId: string }) {
  const router = useRouter();
  const { t } = useI18n();
  const { post, status, loading, error } = useEducationalPost(postId);

  if (loading && !post) {
    return (
      <div className="min-h-dvh bg-background">
        <Container size="sm" className="py-16">
          <Skeleton className="h-10 w-1/2" />
          <Skeleton className="mt-6 aspect-square w-full" />
        </Container>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="min-h-dvh bg-background">
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("education.notFound")}
            description={error ?? undefined}
            action={
              <Button onClick={() => router.push("/create/education")}>
                {t("education.newPost")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  if (post.status === "failed") {
    return (
      <div className="min-h-dvh bg-background">
        <Container size="sm" className="py-16">
          <ErrorState
            title={t("education.failedTitle")}
            description={post.error_message ?? undefined}
            action={
              <Button onClick={() => router.push("/create/education")}>
                {t("education.retry")}
              </Button>
            }
          />
        </Container>
      </div>
    );
  }

  if (post.status !== "ready") {
    return <EducationProgress status={status} />;
  }

  return <ReadyPost post={post} />;
}

function ReadyPost({ post }: { post: EducationalPost }) {
  const { t } = useI18n();
  const { toast } = useToast();
  const displayError = useDisplayError();
  const [savingTheme, setSavingTheme] = useState(false);
  const [savedThemeName, setSavedThemeName] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const postId = post.id;
  const imageUrl = useResolvedAssetUrl(post.image_storage_path);
  const theme = themeLabel(post);
  const showSaveTheme = canSaveGeneratedTheme(post);

  async function handleDownload() {
    if (!imageUrl) return;
    setDownloading(true);
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `afarin-education-${postId}.jpg`;
      link.click();
      URL.revokeObjectURL(objectUrl);
      track("education_post_downloaded", { post_id: postId });
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setDownloading(false);
    }
  }

  async function handleSaveTheme() {
    setSavingTheme(true);
    try {
      const saved = await api.saveEducationalTheme({ post_id: postId });
      setSavedThemeName(saved.name);
      track("education_theme_saved", { post_id: postId, theme_id: saved.id });
      toast(t("education.themeSavedToast", { name: saved.name }));
    } catch (caught) {
      toast(displayError(caught), "error");
    } finally {
      setSavingTheme(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Link href="/dashboard" aria-label={t("nav.dashboard")}>
              <Button variant="ghost" size="sm" className="size-11 p-0 sm:size-9">
                <ArrowBackIcon width={18} height={18} />
              </Button>
            </Link>
            <Logo className="text-base" />
            <PreferencesTrigger />
          </div>
        </Container>
      </header>

      <Container size="sm" className="flex flex-col gap-6 py-8">
        <div>
          <h1 className="text-2xl font-extrabold text-foreground">
            {t("education.resultTitle")}
          </h1>
          {theme ? (
            <p className="mt-2 text-sm text-muted">
              {t("education.themeInUse", { name: theme })}
            </p>
          ) : null}
        </div>

        <div className="overflow-hidden rounded-3xl bg-ink-100 shadow-lift">
          {imageUrl ? (
            // The generated image is the post. No AdCanvas, no overlay text.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={post.headline || t("education.resultTitle")}
              className="aspect-square w-full object-cover"
            />
          ) : (
            <Skeleton className="aspect-square w-full" />
          )}
        </div>

        <Button
          fullWidth
          loading={downloading}
          disabled={!imageUrl}
          onClick={() => void handleDownload()}
          iconStart={<DownloadIcon width={18} height={18} />}
        >
          {t("education.download")}
        </Button>

        {showSaveTheme ? (
          <Card className="flex flex-col gap-3 p-5">
            <p className="text-xs leading-6 text-muted">
              {savedThemeName
                ? t("education.themeInUse", { name: savedThemeName })
                : t("education.themeHint")}
            </p>
            <Button
              variant="outline"
              loading={savingTheme}
              disabled={savedThemeName !== null}
              onClick={() => void handleSaveTheme()}
            >
              {t("education.saveTheme")}
            </Button>
          </Card>
        ) : theme ? (
          <p className="text-sm text-muted">{t("education.themeInUse", { name: theme })}</p>
        ) : null}

        <Link href="/create/education">
          <Button variant="ghost" fullWidth>
            {t("education.newPost")}
          </Button>
        </Link>
      </Container>
    </div>
  );
}
