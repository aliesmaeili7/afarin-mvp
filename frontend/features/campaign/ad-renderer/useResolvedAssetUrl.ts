"use client";

import { useEffect, useState } from "react";
import { api, resolveStaticAssetUrl } from "@/lib/api";

interface Resolved {
  path: string | null;
  url: string | null;
}

/**
 * Turns an opaque `storage_path` into a displayable URL.
 * In Phase 2 this becomes a signed URL without any component change.
 */
export function useResolvedAssetUrl(storagePath: string | null): string | null {
  const [resolved, setResolved] = useState<Resolved>(() => ({
    path: storagePath,
    url: resolveStaticAssetUrl(storagePath),
  }));

  useEffect(() => {
    if (!storagePath) return;

    let active = true;
    void api.resolveAssetUrl(storagePath).then((url) => {
      if (active) setResolved({ path: storagePath, url });
    });

    return () => {
      active = false;
    };
  }, [storagePath]);

  // Returns null while a newly requested path is still resolving, so a stale
  // image is never shown for the wrong asset.
  return resolved.path === storagePath ? resolved.url : null;
}
