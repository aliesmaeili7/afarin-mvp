import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { NextResponse } from "next/server";
import { isDevEvalEnabled, safeFile } from "@/features/dev/creative-eval/fs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ runId: string; path: string[] }> },
) {
  if (!isDevEvalEnabled()) {
    return new NextResponse("Not found", { status: 404 });
  }
  const { runId, path } = await context.params;
  const dest = safeFile(runId, path);
  if (!dest || !existsSync(dest)) {
    return new NextResponse("Not found", { status: 404 });
  }
  const data = await readFile(dest);
  const lower = dest.toLowerCase();
  const type = lower.endsWith(".png")
    ? "image/png"
    : lower.endsWith(".json")
      ? "application/json"
      : lower.endsWith(".txt")
        ? "text/plain; charset=utf-8"
        : "image/jpeg";
  return new NextResponse(data, {
    headers: { "content-type": type, "cache-control": "no-store" },
  });
}
