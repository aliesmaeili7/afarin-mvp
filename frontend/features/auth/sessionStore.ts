"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import type { Session } from "@/types/domain";
import { useWizardStore } from "@/features/campaign/wizard/useWizardStore";

interface SessionState {
  session: Session | null;
  loaded: boolean;
  load: () => Promise<void>;
  setSession: (session: Session | null) => void;
  signOut: () => Promise<void>;
}

/**
 * Who is signed in, as far as the UI is concerned.
 *
 * The actual credential lives in the Supabase client, not here; this only holds
 * the profile the backend returns so components can render a name and a free
 * campaign count.
 */
export const useSessionStore = create<SessionState>()((set) => ({
  session: null,
  loaded: false,
  load: async () => {
    try {
      const session = await api.getSession();
      set({ session, loaded: true });
    } catch {
      // A stale or rejected token must not block the page from rendering; the
      // visitor simply continues as anonymous.
      set({ session: null, loaded: true });
    }
  },
  setSession: (session) => set({ session, loaded: true }),
  signOut: async () => {
    await api.signOut();
    useWizardStore.getState().clear();
    set({ session: null, loaded: true });
  },
}));
