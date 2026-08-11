import type { Metadata } from "next";
import { ObjectiveStep } from "@/features/campaign/wizard/steps/ObjectiveStep";

export const metadata: Metadata = { title: "هدف تبلیغ" };

export default function Page() {
  return <ObjectiveStep />;
}
