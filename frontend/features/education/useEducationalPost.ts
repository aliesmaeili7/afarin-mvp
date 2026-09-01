"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { track } from "@/lib/analytics/track";
import type {
  EducationalPost,
  EducationalPostStatusResponse,
} from "@/types/domain";
import { toDisplayError } from "@/lib/i18n/errors";
import { useI18n } from "@/lib/i18n/PreferencesProvider";

const POLL_INTERVAL_MS = 1200;

/**
 * Loads a post and, while it is still being made, polls until it settles.
 *
 * Polling rather than holding an open request means a refresh or a backgrounded
 * tab resumes wherever the run actually is.
 */
export function useEducationalPost(postId: string) {
  const { locale } = useI18n();
  const [post, setPost] = useState<EducationalPost | null>(null);
  const [status, setStatus] = useState<EducationalPostStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const trackedRef = useRef(false);

  const reload = useCallback(async () => {
    const fresh = await api.getEducationalPost(postId);
    setPost(fresh);
    return fresh;
  }, [postId]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function run() {
      try {
        const current = await api.getEducationalPost(postId);
        if (!active) return;
        setPost(current);
        setLoading(false);

        if (current.status === "ready" || current.status === "failed") {
          if (!trackedRef.current && current.status === "ready") {
            trackedRef.current = true;
            track("education_post_ready", {
              post_id: current.id,
              wall_time_ms: current.wall_time_ms ?? 0,
            });
          }
          return;
        }

        const next = await api.getEducationalPostStatus(postId);
        if (!active) return;
        setStatus(next);
        if (next.status === "ready" || next.status === "failed") {
          await reload();
          if (!active) return;
          if (next.status === "ready" && !trackedRef.current) {
            trackedRef.current = true;
            track("education_post_ready", { post_id: postId });
          }
          return;
        }
      } catch (caught) {
        if (!active) return;
        setLoading(false);
        setError(toDisplayError(caught, locale));
        return;
      }
      if (active) timer = setTimeout(() => void run(), POLL_INTERVAL_MS);
    }

    void run();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [postId, locale, reload]);

  return { post, status, loading, error, setPost, reload };
}
