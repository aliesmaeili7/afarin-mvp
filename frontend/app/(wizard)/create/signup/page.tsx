import { SignupGate } from "@/features/auth/SignupGate";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.signup");

export default function Page() {
  return <SignupGate />;
}
