import { ConceptsStep } from "@/features/campaign/wizard/steps/ConceptsStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardConcepts");

export default function Page() {
  return <ConceptsStep />;
}
