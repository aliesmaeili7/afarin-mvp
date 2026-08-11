import type { Metadata } from "next";
import { ConceptsStep } from "@/features/campaign/wizard/steps/ConceptsStep";

export const metadata: Metadata = { title: "ایده‌های تبلیغ" };

export default function Page() {
  return <ConceptsStep />;
}
