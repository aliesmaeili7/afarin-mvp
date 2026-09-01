"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextAreaField } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/Feedback";
import { ArrowBackIcon } from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useAsyncData } from "@/lib/hooks/useAsyncData";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import type { EducationalThemeList } from "@/types/domain";
import { AuthForm } from "@/features/auth/AuthForm";
import { useSessionStore } from "@/features/auth/sessionStore";
import { AUTO_THEME, ThemePicker, type ThemeChoice } from "./ThemePicker";

const MAX_PROMPT = 2000;
const DRAFT_KEY = "afarin:education-draft";

interface EducationDraft {
  prompt: string;
  choice: ThemeChoice;
  pendingGenerate?: boolean;
}

function readDraft(): EducationDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as EducationDraft;
    if (typeof parsed.prompt !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeDraft(draft: EducationDraft): void {
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

function clearDraft(): void {
  sessionStorage.removeItem(DRAFT_KEY);
}

/**
 * The entire educational brief: one prompt and, optionally, a theme.
 *
 * There is deliberately no field for subject, grade, audience, tone, title or
 * colours. The agent infers all of it, which is what keeps this a single
 * screen instead of a questionnaire.
 */
export function EducationCreatePage() {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();

  const session = useSessionStore((state) => state.session);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);
  const setSession = useSessionStore((state) => state.setSession);

  const [prompt, setPrompt] = useState("");
  const [choice, setChoice] = useState<ThemeChoice>(AUTO_THEME);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const pendingStarted = useRef(false);

  const themes = useAsyncData<EducationalThemeList>(
    () => api.listEducationalThemes(),
    [session?.user.id ?? null],
  );

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    const draft = readDraft();
    const frame = window.requestAnimationFrame(() => {
      if (draft) {
        setPrompt(draft.prompt);
        if (draft.choice) setChoice(draft.choice);
      }
      setDraftLoaded(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!draftLoaded) return;
    writeDraft({
      prompt,
      choice,
      pendingGenerate: readDraft()?.pendingGenerate,
    });
  }, [prompt, choice, draftLoaded]);

  useEffect(() => {
    track("education_create_viewed");
  }, []);

  async function createPost(from?: { prompt: string; choice: ThemeChoice }): Promise<void> {
    const nextPrompt = (from?.prompt ?? prompt).trim();
    const nextChoice = from?.choice ?? choice;
    const post = await api.createEducationalPost({
      user_prompt: nextPrompt,
      theme_id: nextChoice.kind === "saved" ? nextChoice.id : null,
      builtin_theme_id: nextChoice.kind === "builtin" ? nextChoice.id : null,
    });
    clearDraft();
    track("education_post_created", { post_id: post.id, theme: nextChoice.kind });
    if (nextChoice.kind === "saved") {
      track("education_theme_reused", { theme_id: nextChoice.id });
    }
    router.push(`/education/${post.id}`);
  }

  useEffect(() => {
    if (!draftLoaded || !sessionLoaded || !session || pendingStarted.current) {
      return;
    }
    const draft = readDraft();
    if (!draft?.pendingGenerate || !draft.prompt.trim()) return;
    pendingStarted.current = true;
    const nextChoice = draft.choice ?? AUTO_THEME;
    writeDraft({ prompt: draft.prompt, choice: nextChoice });
    const timer = window.setTimeout(() => {
      setSubmitting(true);
      void createPost({ prompt: draft.prompt, choice: nextChoice }).catch(
        (caught: unknown) => {
          toast(displayError(caught), "error");
          setSubmitting(false);
          pendingStarted.current = false;
        },
      );
    }, 0);
    return () => window.clearTimeout(timer);
    // After Google returns, generate from the preserved draft once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftLoaded, sessionLoaded, session]);

  async function handleGenerate() {
    const trimmed = prompt.trim();
    if (!trimmed) {
      setPromptError(t("education.promptRequired"));
      return;
    }
    setPromptError(null);

    // Educational content is authenticated-only, so the account is asked for
    // here rather than earlier: the visitor types first, signs in second.
    if (!session) {
      setNeedsAuth(true);
      return;
    }

    setSubmitting(true);
    try {
      await createPost();
    } catch (caught) {
      toast(displayError(caught), "error");
      setSubmitting(false);
    }
  }

  const overLimit = prompt.length > MAX_PROMPT;

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Link href="/" aria-label={t("common.back")}>
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
          <h1 className="text-2xl font-extrabold text-foreground sm:text-3xl">
            {t("education.title")}
          </h1>
          <p className="mt-2 text-sm leading-7 text-muted">
            {t("education.subtitle")}
          </p>
        </div>

        <TextAreaField
          label={t("education.promptLabel")}
          placeholder={t("education.promptPlaceholder")}
          hint={t("education.promptHint")}
          error={promptError}
          rows={6}
          maxLength={MAX_PROMPT}
          value={prompt}
          onChange={(event) => {
            setPrompt(event.target.value);
            if (promptError) setPromptError(null);
          }}
        />

        {themes.loading && !themes.data ? (
          <Skeleton className="h-28 w-full" />
        ) : (
          <ThemePicker
            builtin={themes.data?.builtin ?? []}
            saved={themes.data?.saved ?? []}
            value={choice}
            onChange={setChoice}
          />
        )}

        <Button
          size="lg"
          fullWidth
          loading={submitting}
          disabled={overLimit}
          onClick={() => void handleGenerate()}
        >
          {t("education.generate")}
        </Button>

        {needsAuth && !session ? (
          <Card className="flex flex-col gap-4 p-5">
            <div>
              <h2 className="text-base font-bold text-foreground">
                {t("education.signInTitle")}
              </h2>
              <p className="mt-1 text-sm leading-7 text-muted">
                {t("education.signInBody")}
              </p>
            </div>
            <AuthForm
              mode="signup"
              submitLabel={t("auth.submitSignup")}
              verifyLabel={t("auth.verifySignup")}
              onEmailStart={() => track("signup_started", { provider: "email" })}
              onVerified={async (next) => {
                setSession(next);
                track("signup_completed", { provider: "email" });
                await createPost();
              }}
              onGoogle={async () => {
                track("signup_started", { provider: "google" });
                writeDraft({ prompt, choice, pendingGenerate: true });
                const redirect = new URL("/create/education", window.location.origin);
                await api.signInWithGoogle({ redirect_to: redirect.toString() });
                const current = await api.getSession();
                if (current) {
                  setSession(current);
                  track("signup_completed", { provider: "google" });
                  await createPost();
                }
              }}
            />
          </Card>
        ) : null}
      </Container>
    </div>
  );
}
