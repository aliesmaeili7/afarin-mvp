"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Container } from "./Container";
import { Logo } from "./Logo";
import { PreferencesTrigger } from "./PreferencesSheet";
import { useSessionStore } from "@/features/auth/sessionStore";
import { beginNewCampaign } from "@/features/campaign/wizard/useWizardStore";
import { useDisplayError, useI18n } from "@/lib/i18n/PreferencesProvider";
import { useToast } from "@/components/ui/Toast";

export function SiteHeader({ showCta = true }: { showCta?: boolean }) {
  const router = useRouter();
  const { toast } = useToast();
  const { t } = useI18n();
  const displayError = useDisplayError();
  const session = useSessionStore((state) => state.session);
  const loaded = useSessionStore((state) => state.loaded);
  const load = useSessionStore((state) => state.load);
  const signOut = useSessionStore((state) => state.signOut);
  const [starting, setStarting] = useState(false);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (!loaded) void load();
  }, [loaded, load]);

  async function handleNewCampaign() {
    setStarting(true);
    try {
      await beginNewCampaign();
      router.push("/create");
    } catch (caught) {
      toast(displayError(caught), "error");
      setStarting(false);
    }
  }

  async function handleSignOut() {
    setLeaving(true);
    try {
      await signOut();
      router.push("/");
    } catch (caught) {
      toast(displayError(caught), "error");
      setLeaving(false);
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-md">
      <Container size="lg" className="flex h-16 items-center justify-between gap-3">
        <Logo />
        {showCta ? (
          <nav className="flex items-center gap-2">
            {!loaded ? null : session ? (
              <>
                <Link
                  href="/dashboard"
                  className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-muted transition-colors hover:bg-ink-100 hover:text-foreground sm:inline-flex"
                >
                  {t("nav.dashboard")}
                </Link>
                <Button size="sm" loading={starting} onClick={() => void handleNewCampaign()}>
                  {t("nav.newCampaign")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={leaving}
                  onClick={() => void handleSignOut()}
                >
                  {t("nav.signOut")}
                </Button>
              </>
            ) : (
              <>
                <Link href="/login">
                  <Button size="sm" variant="ghost">
                    {t("nav.login")}
                  </Button>
                </Link>
                <Link href="/create">
                  <Button size="sm">{t("nav.freeCampaign")}</Button>
                </Link>
              </>
            )}
            <PreferencesTrigger />
          </nav>
        ) : (
          <PreferencesTrigger />
        )}
      </Container>
    </header>
  );
}
