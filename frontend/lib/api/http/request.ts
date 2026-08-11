import { ApiError, type ApiErrorCode } from "../types";
import { getAccessToken } from "@/lib/supabase/client";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const ERROR_CODES = new Set<string>([
  "not_found",
  "validation_error",
  "unauthorized",
  "conflict",
  "upload_failed",
  "generation_failed",
  "rate_limited",
  "unknown",
]);

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
}

/**
 * One request helper for the whole client.
 *
 * `credentials: "include"` is what carries the anonymous session cookie, which
 * is HttpOnly and therefore invisible to this code — the browser attaches it
 * and the backend reads it. That is also why the API's CORS configuration lists
 * exact origins rather than a wildcard.
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers();
  const token = await safeAccessToken();
  if (token) headers.set("authorization", `Bearer ${token}`);

  let body: BodyInit | undefined;
  if (options.formData) {
    // Let the browser set the multipart boundary.
    body = options.formData;
  } else if (options.body !== undefined) {
    headers.set("content-type", "application/json");
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      credentials: "include",
      cache: "no-store",
    });
  } catch (caught) {
    // A dead network must still speak Persian.
    throw new ApiError(
      "unknown",
      "ارتباط با سرور برقرار نشد. اینترنتت رو چک کن.",
      caught,
    );
  }

  if (response.status === 204) return undefined as T;

  if (!response.ok) throw await toApiError(response);

  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as {
      code?: string;
      message_fa?: string;
    };
    if (payload.code && payload.message_fa && ERROR_CODES.has(payload.code)) {
      return new ApiError(payload.code as ApiErrorCode, payload.message_fa);
    }
  } catch {
    // A proxy or gateway can reply with HTML; fall through to the generic text.
  }
  return new ApiError("unknown", "یه مشکلی پیش اومد. لطفاً دوباره امتحان کن.");
}

async function safeAccessToken(): Promise<string | null> {
  try {
    return await getAccessToken();
  } catch {
    // Anonymous visitors have no Supabase client session yet, and that is the
    // normal case for the entire wizard before signup.
    return null;
  }
}
