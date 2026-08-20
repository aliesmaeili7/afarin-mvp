import { ProductStep } from "@/features/campaign/wizard/steps/ProductStep";
import { localeMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = () => localeMetadata("meta.wizardProduct");

export default function Page() {
  return <ProductStep />;
}
