import { NextResponse } from "next/server";
import { isDevEvalEnabled, readRunBundle } from "@/features/dev/creative-eval/fs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ runId: string }> },
) {
  if (!isDevEvalEnabled()) {
    return new NextResponse("Not found", { status: 404 });
  }
  const { runId } = await context.params;
  const bundle = await readRunBundle(runId);
  if (!bundle) {
    return new NextResponse("Not found", { status: 404 });
  }
  return NextResponse.json(bundle);
}
