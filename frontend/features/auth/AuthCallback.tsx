"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, toPersianError } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import { Container } from "@/components/layout/Container";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Feedback";
import { useSessionStore } from "./sessionStore";

/**
 * Finishes a Google sign-in.
 *
 * The Supabase client picks the session out of the URL on its own; what has to
 * happen here is the part the browser cannot do: claim the campaign the visitor
 * built anonymously, then carry on into generation exactly where they left off.
 */
export function AuthCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const setSession = useSessionStore((state) => state.setSession);

  const [error, setError] = useState<string | null>(null);
  // React 18 mounts effects twice in development; adopting twice would be
  // harmless but would fire a duplicate analytics event.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const campaignId = params.get("campaign");

    void (async () => {
      try {
        const session = await api.adoptAnonymousWork();
        setSession(session);

        if (!campaignId) {
          router.replace("/dashboard");
          return;
        }

        track("signup_completed", { provider: "google" });
        await api.startGeneration(campaignId);
        track("generation_started", { campaign_id: campaignId });
        router.replace(`/campaigns/${campaignId}`);
      } catch (caught) {
        setError(toPersianError(caught));
      }
    })();
  }, [params, router, setSession]);

  return (
    <main className="grid min-h-dvh place-items-center bg-ink-50">
      <Container size="sm" className="flex flex-col items-center gap-6 text-center">
        <Logo />
        {error ? (
          <>
            <p className="text-sm leading-7 text-ink-500">{error}</p>
            <Button onClick={() => router.replace("/dashboard")}>
              رفتن به کمپین‌های من
            </Button>
          </>
        ) : (
          <>
            <Skeleton className="h-2 w-40 rounded-full" />
            <p className="text-sm leading-7 text-ink-500">
              یه لحظه صبر کن، داریم واردت می‌کنیم…
            </p>
          </>
        )}
      </Container>
    </main>
  );
}
