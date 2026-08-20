import { LoginPage } from "@/features/auth/LoginPage";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.login");

export default function Page() {
  return <LoginPage />;
}
