import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase in the browser, for authentication only.
 *
 * Every database read and every storage object goes through FastAPI instead, so
 * the browser holds nothing but the publishable key and the user's own access
 * token. The service-role key never leaves the backend (spec §27).
 */
let client: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are required when NEXT_PUBLIC_API_MODE=http",
    );
  }

  client = createClient(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      // Google returns with the session in the URL fragment; /auth/callback
      // needs the client to pick it up rather than ignore it.
      detectSessionInUrl: true,
      flowType: "pkce",
    },
  });
  return client;
}

export async function getAccessToken(): Promise<string | null> {
  const { data } = await getSupabaseClient().auth.getSession();
  return data.session?.access_token ?? null;
}
