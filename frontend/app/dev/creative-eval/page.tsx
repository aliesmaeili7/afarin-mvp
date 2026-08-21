import { notFound } from "next/navigation";
import { RunList } from "@/features/dev/creative-eval/RunList";
import { isDevEvalEnabled, listRuns } from "@/features/dev/creative-eval/fs";

export default async function CreativeEvalIndexPage() {
  if (!isDevEvalEnabled()) {
    notFound();
  }
  const runs = await listRuns();
  return <RunList runs={runs} />;
}
