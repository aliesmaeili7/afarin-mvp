"use client";

import Link from "next/link";

export function RunList({ runs }: { runs: Record<string, unknown>[] }) {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted">Internal only</p>
          <h1 className="text-3xl font-bold">Creative eval</h1>
        </div>
        <Link href="/dev/creative-eval/summary" className="text-sm text-primary underline">
          Recipe summary
        </Link>
      </header>
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
