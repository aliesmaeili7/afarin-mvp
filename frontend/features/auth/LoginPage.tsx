"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { PreferencesTrigger } from "@/components/layout/PreferencesSheet";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { useI18n } from "@/lib/i18n/PreferencesProvider";
import { AuthForm } from "./AuthForm";
import { useSessionStore } from "./sessionStore";

export function LoginPage() {
  const router = useRouter();
  const { t } = useI18n();
  const session = useSessionStore((state) => state.session);
  const sessionLoaded = useSessionStore((state) => state.loaded);
  const loadSession = useSessionStore((state) => state.load);
  const setSession = useSessionStore((state) => state.setSession);

  useEffect(() => {
    if (!sessionLoaded) void loadSession();
  }, [sessionLoaded, loadSession]);

  useEffect(() => {
    if (sessionLoaded && session) router.replace("/dashboard");
  }, [session, sessionLoaded, router]);

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <Container size="sm" className="pt-safe">
          <div className="flex h-14 items-center justify-between gap-2">
            <Logo className="text-base" />
            <div className="flex items-center gap-1">
              <Link href="/create">
                <Button variant="ghost" size="sm">
                  {t("auth.createCampaign")}
                </Button>
              </Link>
              <PreferencesTrigger />
            </div>
          </div>
        </Container>
      </header>

      <Container size="sm" className="flex flex-col gap-6 py-10">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-foreground">{t("auth.loginTitle")}</h1>
          <p className="mt-2 text-sm leading-7 text-muted">{t("auth.loginSubtitle")}</p>
        </div>

        {!sessionLoaded || session ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <>
            <AuthForm
              mode="login"
              submitLabel={t("auth.submitLogin")}
              onVerified={async (next) => {
                setSession(next);
                router.replace("/dashboard");
              }}
              onGoogle={async () => {
                const redirect = new URL("/auth/callback", window.location.origin);
                await api.signInWithGoogle({ redirect_to: redirect.toString() });
                const current = await api.getSession();
                if (current) {
                  setSession(current);
                  router.replace("/dashboard");
                }
              }}
            />
            <p className="text-center text-sm leading-7 text-muted">
              {t("auth.noAccount")}{" "}
              <Link href="/create" className="font-semibold text-brand-700">
                {t("nav.freeCampaign")}
              </Link>
            </p>
          </>
        )}
      </Container>
    </div>
  );
}
