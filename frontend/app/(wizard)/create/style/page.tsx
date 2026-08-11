import type { Metadata } from "next";
import { StyleStep } from "@/features/campaign/wizard/steps/StyleStep";

export const metadata: Metadata = { title: "حس تبلیغ" };

export default function Page() {
  return <StyleStep />;
}
