import { notFound } from "next/navigation";
import { RunReview } from "@/features/dev/creative-eval/RunReview";
import { isDevEvalEnabled, readRunBundle } from "@/features/dev/creative-eval/fs";

export default async function CreativeEvalRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  if (!isDevEvalEnabled()) {
    notFound();
  }
  const { runId } = await params;
  const bundle = await readRunBundle(runId);
  if (!bundle) {
    notFound();
  }
  return <RunReview runId={runId} bundle={bundle} />;
}
