import type { AfarinApi } from "./types";
import { httpApi } from "./http/httpApi";
import { mockApi } from "./mock/mockApi";

/**
 * Single entry point for all data access.
 *
 * Both implementations satisfy the same interface, so the switch happens here
 * and nowhere else: no component, hook or feature module knows which one it is
 * talking to. `mock` keeps Phase 1 runnable with no backend at all, which is
 * what makes the migration reversible.
 */
const apiMode = process.env.NEXT_PUBLIC_API_MODE ?? "mock";

function createApi(): AfarinApi {
  switch (apiMode) {
    case "http":
      return httpApi;
    case "mock":
    default:
      return mockApi;
  }
}

export const api: AfarinApi = createApi();

const PUBLIC_PREFIX = "public://";

/**
 * Synchronous fast path for assets that ship with the app (landing examples,
 * the sample product). Returns null for anything that needs real resolution,
 * which then goes through `api.resolveAssetUrl`. This exists purely so static
 * imagery paints on first render instead of flashing a placeholder.
 */
export function resolveStaticAssetUrl(
  storagePath: string | null,
): string | null {
  if (!storagePath?.startsWith(PUBLIC_PREFIX)) return null;
  return `/${storagePath.slice(PUBLIC_PREFIX.length)}`;
}

export * from "./types";
