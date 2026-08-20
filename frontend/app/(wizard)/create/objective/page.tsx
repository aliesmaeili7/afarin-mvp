import { ObjectiveStep } from "@/features/campaign/wizard/steps/ObjectiveStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardObjective");

export default function Page() {
  return <ObjectiveStep />;
}
