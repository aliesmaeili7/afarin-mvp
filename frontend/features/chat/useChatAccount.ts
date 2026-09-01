"use client";

import { useEffect } from "react";
import { useSessionStore } from "@/features/auth/sessionStore";
import { accountSummaryFromSession } from "./accountSummary";
import { invokeChatSignOut } from "./accountMenu";

/**
 * Chat-facing auth adapter.
 *
 * Session still comes from Afarin's existing store (`api.getSession` /
 * `api.signOut`). Chat never talks to Supabase or a second identity store.
 */
export function useChatAccount() {
  const session = useSessionStore((state) => state.session);
  const loaded = useSessionStore((state) => state.loaded);
  const load = useSessionStore((state) => state.load);
  const signOut = useSessionStore((state) => state.signOut);

  useEffect(() => {
    if (!loaded) void load();
  }, [loaded, load]);

  return {
    account: accountSummaryFromSession(session),
    loaded,
    signOut: () => invokeChatSignOut({ signOut }),
  };
}
