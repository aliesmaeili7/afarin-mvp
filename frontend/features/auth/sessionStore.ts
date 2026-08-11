"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import type { Session } from "@/types/domain";

interface SessionState {
  session: Session | null;
  loaded: boolean;
  load: () => Promise<void>;
  setSession: (session: Session | null) => void;
  signOut: () => Promise<void>;
}

/** Mock auth state. Phase 2 replaces the API calls with Supabase Auth. */
export const useSessionStore = create<SessionState>()((set) => ({
  session: null,
  loaded: false,
  load: async () => {
    const session = await api.getSession();
    set({ session, loaded: true });
  },
  setSession: (session) => set({ session, loaded: true }),
  signOut: async () => {
    await api.signOut();
    set({ session: null });
  },
}));
