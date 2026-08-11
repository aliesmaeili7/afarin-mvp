import type { Metadata } from "next";
import { UploadStep } from "@/features/campaign/wizard/steps/UploadStep";

export const metadata: Metadata = { title: "عکس محصول" };

export default function Page() {
  return <UploadStep />;
}
