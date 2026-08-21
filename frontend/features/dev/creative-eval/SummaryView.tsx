"use client";

export function SummaryView({ rows }: { rows: Record<string, unknown>[] }) {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <p className="text-sm text-muted">
        <a href="/dev/creative-eval" className="underline">
          All runs
        </a>
      </p>
      <h1 className="mb-6 text-3xl font-bold">Recipe summary</h1>
      {rows.length === 0 ? (
        <p className="text-muted">No human ratings yet.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-muted">
              <th className="py-2">Recipe</th>
              <th>n</th>
              <th>Avg overall</th>
              <th>Avg identity</th>
              <th>Avg commercial</th>
              <th>QC hard-fail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.recipe)} className="border-b border-border">
                <td className="py-2 font-medium">{String(row.recipe)}</td>
                <td>{String(row.rated)}</td>
                <td>{String(row.avg_overall ?? "—")}</td>
                <td>{String(row.avg_identity ?? "—")}</td>
                <td>{String(row.avg_commercial ?? "—")}</td>
                <td>{String(row.hard_fail_rate ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
