import { Suspense } from "react";
import { AuthCallback } from "@/features/auth/AuthCallback";

export const metadata = {
  title: "در حال ورود…",
};

/**
 * Where Google sends the user back.
 *
 * Only reachable during OAuth; email sign-in never leaves the app.
 */
export default function AuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <AuthCallback />
    </Suspense>
  );
}
