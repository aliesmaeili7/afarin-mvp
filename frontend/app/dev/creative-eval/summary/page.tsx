import { notFound } from "next/navigation";
import { SummaryView } from "@/features/dev/creative-eval/SummaryView";
import { isDevEvalEnabled, listObservations } from "@/features/dev/creative-eval/fs";

export default async function CreativeEvalSummaryPage() {
  if (!isDevEvalEnabled()) {
    notFound();
  }
  const rows = await listObservations();
  return <SummaryView rows={rows} />;
}
