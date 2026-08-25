import { notFound } from "next/navigation";
import { RunList } from "@/features/dev/creative-eval/RunList";
import { isDevEvalEnabled, listBatches, listRuns } from "@/features/dev/creative-eval/fs";

export default async function CreativeEvalIndexPage() {
  if (!isDevEvalEnabled()) {
    notFound();
  }
  const [runs, batches] = await Promise.all([listRuns(), listBatches()]);
  return <RunList runs={runs} batches={batches} />;
}
