import { NextResponse } from "next/server";
import { isDevEvalEnabled, writeJson } from "@/features/dev/creative-eval/fs";

export async function POST(
  request: Request,
  context: { params: Promise<{ runId: string }> },
) {
  if (!isDevEvalEnabled()) {
    return new NextResponse("Not found", { status: 404 });
  }
  const { runId } = await context.params;
  const payload = (await request.json()) as unknown;
  await writeJson(runId, "ratings.json", payload);
  return NextResponse.json({ ok: true });
}
