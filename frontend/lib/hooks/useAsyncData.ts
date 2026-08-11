"use client";

import { useCallback, useEffect, useState } from "react";
import { toPersianError } from "@/lib/api";

export interface AsyncDataState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (value: T | null) => void;
}

interface InternalState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Minimal data-fetching hook over the API layer.
 *
 * Deliberately not a caching library: Phase 1 has a handful of screens and
 * every call already goes through the swappable API boundary. State is only
 * ever updated from a promise callback or during render (the React-sanctioned
 * "adjust state when inputs change" pattern), never synchronously in an effect.
 */
export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncDataState<T> {
  const key = JSON.stringify(deps);

  const [state, setState] = useState<InternalState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const [renderedKey, setRenderedKey] = useState(key);
  const [nonce, setNonce] = useState(0);

  if (key !== renderedKey) {
    setRenderedKey(key);
    setState((current) => ({ ...current, loading: true }));
  }

  useEffect(() => {
    let cancelled = false;

    loader()
      .then((result) => {
        if (!cancelled) setState({ data: result, error: null, loading: false });
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            error: toPersianError(caught),
            loading: false,
          }));
        }
      });

    return () => {
      cancelled = true;
    };
    // `loader` is intentionally excluded: it is recreated on every render, and
    // the request should only be repeated when `deps` change or on reload().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce]);

  const reload = useCallback(async () => {
    setNonce((current) => current + 1);
  }, []);

  const setData = useCallback((value: T | null) => {
    setState((current) => ({ ...current, data: value }));
  }, []);

  return { ...state, reload, setData };
}
