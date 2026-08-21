import { DirectionsStep } from "@/features/campaign/wizard/steps/DirectionsStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardDirections");

export default function Page() {
  return <DirectionsStep />;
}
