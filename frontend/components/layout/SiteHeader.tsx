"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Container } from "./Container";
import { Logo } from "./Logo";
import { useSessionStore } from "@/features/auth/sessionStore";
import { beginNewCampaign } from "@/features/campaign/wizard/useWizardStore";
import { toPersianError } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

export function SiteHeader({ showCta = true }: { showCta?: boolean }) {
  const router = useRouter();
  const { toast } = useToast();
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
      toast(toPersianError(caught), "error");
      setStarting(false);
    }
  }

  async function handleSignOut() {
    setLeaving(true);
    try {
      await signOut();
      router.push("/");
    } catch (caught) {
      toast(toPersianError(caught), "error");
      setLeaving(false);
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100/80 bg-ink-50/85 backdrop-blur-md">
      <Container size="lg" className="flex h-16 items-center justify-between gap-3">
        <Logo />
        {showCta ? (
          <nav className="flex items-center gap-2">
            {!loaded ? null : session ? (
              <>
                <Link
                  href="/dashboard"
                  className="rounded-xl px-3 py-2 text-sm font-semibold text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900"
                >
                  داشبورد
                </Link>
                <Button size="sm" loading={starting} onClick={() => void handleNewCampaign()}>
                  کمپین جدید
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={leaving}
                  onClick={() => void handleSignOut()}
                >
                  خروج
                </Button>
              </>
            ) : (
              <>
                <Link href="/login">
                  <Button size="sm" variant="ghost">
                    ورود
                  </Button>
                </Link>
                <Link href="/create">
                  <Button size="sm">ساخت کمپین رایگان</Button>
                </Link>
              </>
            )}
          </nav>
        ) : null}
      </Container>
    </header>
  );
}
