import { Suspense } from "react";
import { AuthCallback } from "@/features/auth/AuthCallback";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.authCallback");

/**
 * Where Google (and a misdirected recovery link) sends the user back.
 *
 * Password recovery itself lands on /auth/reset-password. If a hosted
 * project still points recovery at this route, we forward it.
 */
export default function AuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <AuthCallback />
    </Suspense>
  );
}
