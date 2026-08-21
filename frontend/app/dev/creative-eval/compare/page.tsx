import { notFound } from "next/navigation";
import { CompareView } from "@/features/dev/creative-eval/CompareView";
import { isDevEvalEnabled, listRuns } from "@/features/dev/creative-eval/fs";

export default async function CreativeEvalComparePage() {
  if (!isDevEvalEnabled()) {
    notFound();
  }
  const runs = await listRuns();
  return <CompareView runs={runs} />;
}
