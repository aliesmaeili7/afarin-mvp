import { StyleStep } from "@/features/campaign/wizard/steps/StyleStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardStyle");

export default function Page() {
  return <StyleStep />;
}
