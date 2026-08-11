import type { Metadata } from "next";
import { ProductStep } from "@/features/campaign/wizard/steps/ProductStep";

export const metadata: Metadata = { title: "درباره محصول" };

export default function Page() {
  return <ProductStep />;
}
