"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { RatingsPanel, type CandidateRating } from "./RatingsPanel";

type RecipeBundle = {
  folder: string;
  recipe: { style_id?: string; template_id?: string; title_fa?: string } | null;
  direction: Record<string, unknown> | null;
  prompt: string | null;
  quality: { candidates?: Record<string, unknown>[] } | null;
  metrics: { frames?: Record<string, unknown>[] } | null;
  error: { error?: string } | null;
  files: string[];
};

type RatingsState = {
  candidates: Record<string, CandidateRating>;
  director: {
    overall?: number;
    analysis_correct?: number;
    directions_different?: number;
    recipe_fit?: number;
    note?: string;
    per_direction?: Record<string, { overall?: number; note?: string }>;
  };
};

function fileUrl(runId: string, folder: string | null, name: string): string {
  const parts = folder ? `recipes/${folder}/${name}` : name;
  return `/api/dev/creative-eval/runs/${encodeURIComponent(runId)}/file/${parts}`;
}

function qcFor(quality: RecipeBundle["quality"], slot: number) {
  return quality?.candidates?.find((item) => item.slot === slot) ?? null;
}

export function RunReview({
  runId,
  bundle,
}: {
  runId: string;
  bundle: Record<string, unknown>;
}) {
  const meta = (bundle.meta ?? {}) as Record<string, unknown>;
  const brief = (bundle.brief ?? {}) as Record<string, unknown>;
  const director = bundle.director as Record<string, unknown> | null;
  const cost = (bundle.cost ?? {}) as Record<string, unknown>;
  const recipes = (bundle.recipes ?? []) as RecipeBundle[];
  const [ratings, setRatings] = useState<RatingsState>(
    (bundle.ratings as RatingsState) ?? { candidates: {}, director: {} },
  );
  const [saved, setSaved] = useState("");

  const mode = String(meta.mode ?? "fixed");
  const llm = (cost.llm_calls ?? {}) as Record<string, unknown>;
  const images = (cost.image_outputs ?? {}) as Record<string, unknown>;
  const usd = (cost.cost_usd ?? {}) as Record<string, unknown>;

  async function persist(next: RatingsState) {
    setRatings(next);
    await fetch(`/api/dev/creative-eval/runs/${encodeURIComponent(runId)}/ratings`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(next),
    });
    setSaved("saved");
  }

  const directorDirections = useMemo(() => {
    const rows = director?.directions;
    return Array.isArray(rows) ? (rows as Record<string, unknown>[]) : [];
  }, [director]);

  return (
    <main className="mx-auto max-w-[1600px] px-6 py-8">
      <p className="text-sm text-muted">
        <Link href="/dev/creative-eval" className="underline">
          All runs
        </Link>{" "}
        ·{" "}
        <Link href="/dev/creative-eval/summary" className="underline">
          Summary
        </Link>
      </p>
      <h1 className="mt-2 text-3xl font-bold">{runId}</h1>
      <p className="text-muted">
        {String(meta.case_id)} · {mode} · label {String(meta.label ?? "—")} · prompt{" "}
        {String(meta.prompt_version)} · {String(meta.provider)}
      </p>

      <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(280px,420px)_1fr]">
        <div>
          <h2 className="mb-2 text-lg font-semibold">Reference product</h2>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={fileUrl(runId, null, "reference_product.jpg")}
            alt="Reference product"
            className="w-full rounded-2xl border border-border object-contain"
          />
        </div>
        <div className="space-y-3 text-sm">
          <h2 className="text-lg font-semibold">Brief</h2>
          <dl className="grid grid-cols-2 gap-2">
            {Object.entries(brief).map(([key, value]) => (
              <div key={key}>
                <dt className="text-muted">{key}</dt>
                <dd>{Array.isArray(value) ? value.join(", ") : String(value ?? "—")}</dd>
              </div>
            ))}
          </dl>
          <div className="rounded-2xl border border-border p-4">
            <h3 className="font-semibold">Cost / calls</h3>
            <p>
              LLM — Director: {String(llm.director ?? 0)}, QC: {String(llm.qc ?? 0)}
            </p>
            <p>
              Images — candidates {String(images.candidates ?? 0)}, repairs{" "}
              {String(images.repairs ?? 0)}, story {String(images.story ?? 0)}, master{" "}
              {String(images.master ?? 0)}, total {String(images.total ?? 0)}
            </p>
            <p>USD — images {String(usd.images ?? "—")}, total {String(usd.total ?? "—")}</p>
          </div>
        </div>
      </section>

      {director ? (
        <section className="mt-10 rounded-2xl border border-border p-5">
          <h2 className="text-xl font-semibold">Director</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm">{String(director.product_visual_analysis ?? "")}</p>
          <p className="mt-2 text-sm text-muted">
            type {String(director.product_type)} · identity{" "}
            {Array.isArray(director.visual_identity)
              ? director.visual_identity.join(", ")
              : ""}
          </p>
          <p className="text-sm">
            unsuitable styles: {String((director.unsuitable_style_ids as string[] | undefined)?.join(", ") || "—")}
          </p>
          <DirectorRatings
            value={ratings.director}
            directions={directorDirections}
            onChange={(directorNext) => persist({ ...ratings, director: directorNext })}
          />
        </section>
      ) : null}

      <div className="mt-10 space-y-16">
        {recipes.map((item, index) => (
          <RecipeBlock
            key={item.folder}
            runId={runId}
            item={item}
            index={index}
            mode={mode}
            ratings={ratings}
            onRate={(key, value) =>
              persist({
                ...ratings,
                candidates: { ...ratings.candidates, [key]: value },
              })
            }
          />
        ))}
      </div>
      {saved ? <p className="mt-6 text-sm text-mint-600">{saved}</p> : null}
    </main>
  );
}

function RecipeBlock({
  runId,
  item,
  index,
  mode,
  ratings,
  onRate,
}: {
  runId: string;
  item: RecipeBundle;
  index: number;
  mode: string;
  ratings: RatingsState;
  onRate: (key: string, value: CandidateRating) => void;
}) {
  const styleId = String(item.recipe?.style_id ?? "");
  const templateId = String(item.recipe?.template_id ?? "");
  const direction = item.direction ?? {};
  const candidates = [1, 2, 3].filter((slot) =>
    item.files.includes(`candidate-${slot}.jpg`),
  );
  return (
    <section>
      <h2 className="text-2xl font-bold">
        {mode === "director" ? `Direction ${index + 1} · ` : null}
        {styleId} × {templateId}
      </h2>
      {item.direction ? (
        <div className="mt-2 max-w-3xl text-sm">
          <p className="font-semibold">{String(direction.title_fa ?? "")}</p>
          <p>{String(direction.angle ?? "")}</p>
          <p>{String(direction.headline_fa ?? "")}</p>
          <p className="text-muted">{String(direction.visual_direction ?? "")}</p>
          <p className="text-muted">
            constraints: {String((direction.identity_constraints as string[] | undefined)?.join("; ") ?? "—")}
          </p>
          {direction.warning_fa ? (
            <p className="text-danger">{String(direction.warning_fa)}</p>
          ) : null}
        </div>
      ) : null}
      {item.error ? (
        <p className="mt-2 text-danger">{item.error.error}</p>
      ) : null}

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <PreviewCard
          label="Public style preview"
          src={`/visual-previews/styles/${styleId}.jpg`}
        />
        <PreviewCard
          label="Public template preview"
          src={`/visual-previews/templates/${templateId}.jpg`}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {candidates.map((slot) => {
          const key = `${item.folder}:${slot}`;
          const qc = qcFor(item.quality, slot);
          return (
            <article key={slot} className="min-w-0">
              <p className="mb-2 font-semibold">Candidate {slot}</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={fileUrl(runId, item.folder, `candidate-${slot}.jpg`)}
                alt={`Candidate ${slot}`}
                className="w-full rounded-xl border border-border object-contain"
              />
              <QcBlock qc={qc} />
              <RatingsPanel
                value={ratings.candidates[key] ?? {}}
                onChange={(value) => onRate(key, value)}
              />
            </article>
          );
        })}
      </div>

      {item.prompt ? (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-muted">Effective prompt</summary>
          <pre className="mt-2 whitespace-pre-wrap rounded-xl bg-ink-950/80 p-3 text-ink-50">
            {item.prompt}
          </pre>
        </details>
      ) : null}

      {item.files.includes("story.jpg") || item.files.includes("master-9x16.jpg") ? (
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {item.files.includes("candidate-1.jpg") ? (
            <PreviewCard
              label="A · dedicated 4:5"
              src={fileUrl(runId, item.folder, "candidate-1.jpg")}
            />
          ) : null}
          {item.files.includes("story.jpg") ? (
            <PreviewCard
              label="B · dedicated 9:16 Story"
              src={fileUrl(runId, item.folder, "story.jpg")}
            />
          ) : null}
          {item.files.includes("master-9x16.jpg") ? (
            <PreviewCard
              label="C · 9:16 master"
              src={fileUrl(runId, item.folder, "master-9x16.jpg")}
            />
          ) : null}
          {item.files.includes("crop-4x5.jpg") ? (
            <PreviewCard
              label="C · 4:5 crop"
              src={fileUrl(runId, item.folder, "crop-4x5.jpg")}
            />
          ) : null}
        </div>
      ) : null}

      {item.files.includes("repair-1.jpg") ? (
        <div className="mt-4">
          <PreviewCard
            label="Repair"
            src={fileUrl(runId, item.folder, "repair-1.jpg")}
          />
        </div>
      ) : null}
    </section>
  );
}

function PreviewCard({ label, src }: { label: string; src: string }) {
  return (
    <figure>
      <figcaption className="mb-1 text-sm text-muted">{label}</figcaption>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={label} className="w-full rounded-xl border border-border object-contain" />
    </figure>
  );
}

function QcBlock({ qc }: { qc: Record<string, unknown> | null }) {
  if (!qc) {
    return <p className="mt-2 text-xs text-muted">AUTO QC: not run</p>;
  }
  const failed = Boolean(qc.hard_failed);
  return (
    <div className={`mt-2 rounded-lg p-2 text-xs ${failed ? "bg-coral-100" : "bg-mint-100"}`}>
      <p className="font-semibold">AUTO QC: {failed ? "hard fail" : "pass"}</p>
      {Array.isArray(qc.reasons) && qc.reasons.length ? (
        <p>{(qc.reasons as string[]).join("; ")}</p>
      ) : null}
    </div>
  );
}

function DirectorRatings({
  value,
  directions,
  onChange,
}: {
  value: RatingsState["director"];
  directions: Record<string, unknown>[];
  onChange: (next: RatingsState["director"]) => void;
}) {
  const fields = [
    ["overall", "Overall Director"],
    ["analysis_correct", "Visual analysis correct"],
    ["directions_different", "3 directions different"],
    ["recipe_fit", "Recipes fit product / objective"],
  ] as const;
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      {fields.map(([key, label]) => (
        <label key={key} className="flex items-center justify-between text-sm">
          {label}
          <select
            className="rounded-md border border-border bg-surface px-2 py-1"
            value={value[key] ?? ""}
            onChange={(event) =>
              onChange({
                ...value,
                [key]: event.target.value ? Number(event.target.value) : undefined,
              })
            }
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((score) => (
              <option key={score} value={score}>
                {score}
              </option>
            ))}
          </select>
        </label>
      ))}
      {directions.map((item, index) => {
        const key = String(index + 1);
        const row = value.per_direction?.[key] ?? {};
        return (
          <label key={key} className="flex items-center justify-between text-sm">
            Direction {key} ({String(item.style_id)} × {String(item.template_id)})
            <select
              className="rounded-md border border-border bg-surface px-2 py-1"
              value={row.overall ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  per_direction: {
                    ...value.per_direction,
                    [key]: {
                      ...row,
                      overall: event.target.value ? Number(event.target.value) : undefined,
                    },
                  },
                })
              }
            >
              <option value="">—</option>
              {[1, 2, 3, 4, 5].map((score) => (
                <option key={score} value={score}>
                  {score}
                </option>
              ))}
            </select>
          </label>
        );
      })}
      <textarea
        className="md:col-span-2 rounded-md border border-border bg-surface p-2 text-sm"
        rows={2}
        placeholder="Director note"
        value={value.note ?? ""}
        onChange={(event) => onChange({ ...value, note: event.target.value })}
      />
    </div>
  );
}
