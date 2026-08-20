import { VisualStep } from "@/features/campaign/wizard/steps/VisualStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardVisual");

export default function Page() {
  return <VisualStep />;
}
