"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type RecipeBundle = {
  folder: string;
  recipe: { style_id?: string; template_id?: string } | null;
  prompt: string | null;
  promptJson?: { prompt_version?: string } | null;
  quality: { candidates?: Record<string, unknown>[] } | null;
  metrics: { frames?: Record<string, unknown>[] } | null;
  files: string[];
};

type CandidateRating = {
  overall?: number;
  identity?: number;
  attractiveness?: number;
  style_match?: number;
  template_match?: number;
  commercial?: number;
  flags?: string[];
  note?: string;
};

type Bundle = {
  meta: Record<string, unknown>;
  cost: Record<string, unknown> | null;
  ratings: { candidates?: Record<string, CandidateRating> };
  recipes: RecipeBundle[];
};

function fileUrl(runId: string, folder: string, name: string): string {
  return `/api/dev/creative-eval/runs/${encodeURIComponent(runId)}/file/recipes/${folder}/${name}`;
}

function recipeKey(item: RecipeBundle): string {
  const style = item.recipe?.style_id;
  const template = item.recipe?.template_id;
  if (style && template) {
    return `${style}:${template}`;
  }
  return item.folder.replace(/^\d+_/, "").replace("__", ":");
}

function candidateSrc(runId: string, item: RecipeBundle): string | null {
  const name = item.files.find((file) => /^candidate-1\.(jpg|jpeg|png)$/i.test(file));
  return name ? fileUrl(runId, item.folder, name) : null;
}

function qcFor(quality: RecipeBundle["quality"]) {
  return quality?.candidates?.find((item) => item.slot === 1) ?? null;
}

function latency(metrics: RecipeBundle["metrics"]): string {
  const frame = metrics?.frames?.find((item) => item.kind === "candidate" || item.slot === 1);
  if (!frame) {
    return "—";
  }
  const ms = frame.latency_ms ?? frame.duration_ms;
  return ms != null ? String(ms) : "—";
}

function costFor(metrics: RecipeBundle["metrics"]): string {
  const frame = metrics?.frames?.find((item) => item.kind === "candidate" || item.slot === 1);
  if (!frame) {
    return "—";
  }
  const usd = frame.cost_usd;
  return usd != null ? String(usd) : "—";
}

function HumanScores({ rating }: { rating?: CandidateRating }) {
  if (!rating) {
    return <p className="text-sm text-muted">No human scores</p>;
  }
  return (
    <dl className="grid grid-cols-2 gap-1 text-sm">
      {(
        [
          ["overall", rating.overall],
          ["identity", rating.identity],
          ["attractiveness", rating.attractiveness],
          ["style", rating.style_match],
          ["template", rating.template_match],
          ["commercial", rating.commercial],
        ] as const
      ).map(([label, value]) => (
        <div key={label}>
          <dt className="text-muted">{label}</dt>
          <dd>{value ?? "—"}</dd>
        </div>
      ))}
      {rating.flags?.length ? (
        <div className="col-span-2">
          <dt className="text-muted">flags</dt>
          <dd>{rating.flags.join(", ")}</dd>
        </div>
      ) : null}
      {rating.note ? (
        <div className="col-span-2">
          <dt className="text-muted">note</dt>
          <dd>{rating.note}</dd>
        </div>
      ) : null}
    </dl>
  );
}

function Side({
  title,
  runId,
  bundle,
  item,
}: {
  title: string;
  runId: string;
  bundle: Bundle;
  item: RecipeBundle | null;
}) {
  const meta = bundle.meta;
  const src = item ? candidateSrc(runId, item) : null;
  const qc = item ? qcFor(item.quality) : null;
  const ratingKey = item ? `${item.folder}:1` : "";
  return (
    <section className="rounded-2xl border border-border p-4">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="text-sm text-muted">{runId}</p>
      <p className="mt-1 text-sm">
        prompt {String(meta.prompt_version ?? item?.promptJson?.prompt_version ?? "—")} · model{" "}
        {String(meta.image_model ?? "—")} · {String(meta.provider ?? "")}
      </p>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={title} className="mt-3 w-full rounded-xl border border-border object-contain" />
      ) : (
        <p className="mt-3 text-sm text-muted">No candidate image</p>
      )}
      <div className="mt-4">
        <h3 className="text-sm font-semibold">Human scores</h3>
        <HumanScores rating={bundle.ratings.candidates?.[ratingKey]} />
      </div>
      <div className="mt-3 text-sm">
        <h3 className="font-semibold">AUTO QC</h3>
        {qc ? (
          <p className={qc.hard_failed ? "text-coral-700" : ""}>
            {qc.hard_failed ? "hard fail" : "pass"}
            {Array.isArray(qc.reasons) ? ` — ${(qc.reasons as string[]).join("; ")}` : ""}
          </p>
        ) : (
          <p className="text-muted">not run</p>
        )}
      </div>
      <p className="mt-3 text-sm text-muted">
        latency {item ? latency(item.metrics) : "—"} · cost {item ? costFor(item.metrics) : "—"}
      </p>
    </section>
  );
}

export function CompareView({ runs }: { runs: Record<string, unknown>[] }) {
  const [leftId, setLeftId] = useState(String(runs[0]?.run_id ?? ""));
  const [rightId, setRightId] = useState(String(runs[1]?.run_id ?? runs[0]?.run_id ?? ""));
  const [left, setLeft] = useState<Bundle | null>(null);
  const [right, setRight] = useState<Bundle | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    const [a, b] = await Promise.all([
      fetch(`/api/dev/creative-eval/runs/${encodeURIComponent(leftId)}`).then((res) =>
        res.ok ? res.json() : null,
      ),
      fetch(`/api/dev/creative-eval/runs/${encodeURIComponent(rightId)}`).then((res) =>
        res.ok ? res.json() : null,
      ),
    ]);
    if (!a || !b) {
      setError("Could not load one of the runs.");
      return;
    }
    setLeft(a as Bundle);
    setRight(b as Bundle);
  }

  const pairs = useMemo(() => {
    if (!left || !right) {
      return [];
    }
    if (String(left.meta.case_id ?? "") !== String(right.meta.case_id ?? "")) {
      return [];
    }
    const rightMap = new Map(right.recipes.map((item) => [recipeKey(item), item]));
    const keys = new Set([
      ...left.recipes.map(recipeKey),
      ...right.recipes.map(recipeKey),
    ]);
    return [...keys].sort().map((key) => ({
      key,
      left: left.recipes.find((item) => recipeKey(item) === key) ?? null,
      right: rightMap.get(key) ?? null,
    }));
  }, [left, right]);

  return (
    <main className="mx-auto max-w-[1600px] px-6 py-8">
      <p className="text-sm text-muted">
        <Link href="/dev/creative-eval" className="underline">
          All runs
        </Link>
        {" · "}
        <Link href="/dev/creative-eval/summary" className="underline">
          Summary
        </Link>
      </p>
      <h1 className="mt-2 text-3xl font-bold">Compare runs</h1>
      <p className="text-sm text-muted">
        Same case + recipe, side by side. No automatic winner.
      </p>
      <div className="mt-6 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
        <label className="text-sm">
          Baseline
          <select
            className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1"
            value={leftId}
            onChange={(event) => setLeftId(event.target.value)}
          >
            {runs.map((run) => (
              <option key={String(run.run_id)} value={String(run.run_id)}>
                {String(run.run_id)} · {String(run.label ?? "no label")}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Challenger
          <select
            className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1"
            value={rightId}
            onChange={(event) => setRightId(event.target.value)}
          >
            {runs.map((run) => (
              <option key={String(run.run_id)} value={String(run.run_id)}>
                {String(run.run_id)} · {String(run.label ?? "no label")}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="self-end rounded-md bg-primary px-4 py-2 text-sm text-white"
          onClick={() => void load()}
        >
          Compare
        </button>
      </div>
      {error ? <p className="mt-4 text-sm text-coral-700">{error}</p> : null}
      {left && right && String(left.meta.case_id ?? "") !== String(right.meta.case_id ?? "") ? (
        <p className="mt-4 text-sm text-coral-700">
          These runs are different cases ({String(left.meta.case_id)} vs{" "}
          {String(right.meta.case_id)}). Pick two runs of the same case.
        </p>
      ) : null}
      {pairs.map((pair) => (
        <section key={pair.key} className="mt-10">
          <h2 className="mb-3 text-lg font-semibold">{pair.key}</h2>
          {left && right ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <Side title={String(left.meta.label ?? "Baseline")} runId={leftId} bundle={left} item={pair.left} />
              <Side
                title={String(right.meta.label ?? "Challenger")}
                runId={rightId}
                bundle={right}
                item={pair.right}
              />
            </div>
          ) : null}
        </section>
      ))}
    </main>
  );
}
