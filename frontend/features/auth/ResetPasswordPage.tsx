"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { Skeleton } from "@/components/ui/Feedback";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import { useSessionStore } from "./sessionStore";

const MIN_PASSWORD = 8;

export function ResetPasswordPage() {
  const router = useRouter();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const setSession = useSessionStore((state) => state.setSession);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void api
      .ensurePasswordRecoverySession()
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setLinkError(displayError(caught));
      });
    return () => {
      cancelled = true;
    };
  }, [displayError]);

  async function handleSave() {
    if (password.length < MIN_PASSWORD) {
      setError(t("errors.passwordMin"));
      return;
    }
    if (password !== confirm) {
      setError(t("errors.passwordMismatch"));
      return;
    }

    setSubmitting(true);
    try {
      const session = await api.updatePassword({ password });
      setSession(session);
      router.replace("/dashboard");
    } catch (caught) {
      setError(displayError(caught));
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Logo className="text-base" />
            <div className="flex items-center gap-1">
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  {t("nav.login")}
                </Button>
              </Link>
              <PreferencesTrigger />
            </div>
          </div>
        </Container>
      </header>

      <Container size="sm" className="flex flex-col gap-6 py-10">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-foreground">
            {t("auth.choosePasswordTitle")}
          </h1>
          <p className="mt-2 text-sm leading-7 text-muted">
            {t("auth.choosePasswordSubtitle")}
          </p>
        </div>

        {linkError ? (
          <Card className="flex flex-col gap-4 p-5 text-center">
            <p className="text-sm leading-7 text-muted">{linkError}</p>
            <Link href="/login">
              <Button fullWidth>{t("auth.backToLogin")}</Button>
            </Link>
          </Card>
        ) : !ready ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <Card className="flex flex-col gap-4 p-5">
            <TextField
              label={t("auth.password")}
              type="password"
              autoComplete="new-password"
              hint={t("auth.passwordHint")}
              value={password}
              error={error}
              onChange={(event) => {
                setPassword(event.target.value);
                setError(null);
              }}
            />
            <TextField
              label={t("auth.confirmPassword")}
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => {
                setConfirm(event.target.value);
                setError(null);
              }}
            />
            <Button
              size="lg"
              fullWidth
              loading={submitting}
              onClick={() => void handleSave()}
            >
              {t("auth.savePassword")}
            </Button>
          </Card>
        )}
      </Container>
    </div>
  );
}
