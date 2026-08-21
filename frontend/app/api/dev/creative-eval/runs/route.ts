import { NextResponse } from "next/server";
import { isDevEvalEnabled, listRuns } from "@/features/dev/creative-eval/fs";

export async function GET() {
  if (!isDevEvalEnabled()) {
    return new NextResponse("Not found", { status: 404 });
  }
  return NextResponse.json(await listRuns());
}
