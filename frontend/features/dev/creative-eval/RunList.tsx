"use client";

import Link from "next/link";

function waitLabel(ms: unknown): string | null {
  if (typeof ms !== "number" || !Number.isFinite(ms)) {
    return null;
  }
  return `${(ms / 1000).toFixed(1)} s`;
}

export function RunList({
  runs,
  batches = [],
}: {
  runs: Record<string, unknown>[];
  batches?: Record<string, unknown>[];
}) {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted">Internal only</p>
          <h1 className="text-3xl font-bold">Creative eval</h1>
        </div>
        <div className="flex gap-4 text-sm">
          <Link href="/dev/creative-eval/compare" className="text-primary underline">
            Compare
          </Link>
          <Link href="/dev/creative-eval/summary" className="text-primary underline">
            Recipe summary
          </Link>
        </div>
      </header>
      {batches.length > 0 ? (
        <section className="mb-8 rounded-2xl border border-border p-4">
          <h2 className="text-lg font-semibold">Experiment batches</h2>
          <ul className="mt-3 grid gap-2 text-sm">
            {batches.map((batch) => (
              <li key={String(batch.file ?? batch.experiment_id)}>
                <div className="font-medium">{String(batch.experiment_id ?? batch.file)}</div>
                <div className="text-muted">
                  TOTAL WAIT {waitLabel(batch.wall_time_ms) ?? "—"} ·{" "}
                  {Array.isArray(batch.runs) ? `${batch.runs.length} runs` : "—"}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {runs.length === 0 ? (
        <p className="text-muted">
          No runs yet. From backend/:{" "}
          <code>uv run python -m scripts.run_creative_eval --case sweatshirt_01 --mode fixed --dry-run</code>
        </p>
      ) : (
        <ul className="grid gap-3">
          {runs.map((run) => {
            const id = String(run.run_id ?? "");
            return (
              <li key={id}>
                <Link
                  href={`/dev/creative-eval/${id}`}
                  className="block rounded-2xl border border-border bg-surface p-4 hover:border-primary"
                >
                  <div className="font-semibold">{id}</div>
                  <div className="mt-1 text-sm text-muted">
                    {String(run.case_id ?? "")} · {String(run.mode ?? "")} ·{" "}
                    {String(run.label ?? "no label")} · {String(run.provider ?? "")}
                    {waitLabel(run.wall_time_ms)
                      ? ` · TOTAL WAIT ${waitLabel(run.wall_time_ms)}`
                      : ""}
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
