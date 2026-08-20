import { UploadStep } from "@/features/campaign/wizard/steps/UploadStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardPhoto");

export default function Page() {
  return <UploadStep />;
}
