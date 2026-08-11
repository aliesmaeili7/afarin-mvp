import type { AfarinApi } from "./types";
import { mockApi } from "./mock/mockApi";

/**
 * Single entry point for all data access.
 *
 * Phase 1 ships only the mock implementation. Phase 2 adds an HTTP client that
 * talks to FastAPI and selects it here via NEXT_PUBLIC_API_MODE — no component,
 * hook or feature module changes.
 */
const apiMode = process.env.NEXT_PUBLIC_API_MODE ?? "mock";

function createApi(): AfarinApi {
  switch (apiMode) {
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
