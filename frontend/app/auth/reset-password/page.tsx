import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.resetPassword");

export default function Page() {
  return <ResetPasswordPage />;
}
