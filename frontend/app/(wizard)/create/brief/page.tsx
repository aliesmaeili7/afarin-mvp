import { BriefStep } from "@/features/campaign/wizard/steps/BriefStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardBrief");

export default function Page() {
  return <BriefStep />;
}
