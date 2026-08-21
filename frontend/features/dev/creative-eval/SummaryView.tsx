"use client";

import { useMemo, useState } from "react";
import type { SummaryObservation } from "./types";

const GROUP_OPTIONS = [
  { id: "case_recipe", label: "case + recipe" },
  { id: "case", label: "case" },
  { id: "category", label: "category" },
  { id: "style", label: "style" },
  { id: "template", label: "template" },
  { id: "recipe", label: "recipe" },
  { id: "label", label: "label / prompt version" },
  { id: "mode", label: "mode" },
  { id: "image_model", label: "image model" },
] as const;

function unique(values: (string | null)[]): string[] {
  return [...new Set(values.filter((item): item is string => Boolean(item)))].sort();
}

function groupKey(row: SummaryObservation, groupBy: string): string {
  switch (groupBy) {
    case "case":
      return row.case_id || "(no case)";
    case "category":
      return row.category || "(no category)";
    case "style":
      return row.style_id || "(no style)";
    case "template":
      return row.template_id || "(no template)";
    case "recipe":
      return row.recipe;
    case "label":
      return `${row.label ?? "(no label)"} / ${row.prompt_version ?? "?"}`;
    case "mode":
      return row.mode || "(no mode)";
    case "image_model":
      return row.image_model || "(no model)";
    default:
      return `${row.case_id || "?"} · ${row.recipe}`;
  }
}

function avg(values: number[]): number | null {
  if (!values.length) {
    return null;
  }
  return Math.round((values.reduce((sum, item) => sum + item, 0) / values.length) * 100) / 100;
}

export function SummaryView({ rows }: { rows: SummaryObservation[] }) {
  const [caseId, setCaseId] = useState("");
  const [category, setCategory] = useState("");
  const [style, setStyle] = useState("");
  const [template, setTemplate] = useState("");
  const [label, setLabel] = useState("");
  const [mode, setMode] = useState("");
  const [imageModel, setImageModel] = useState("");
  const [groupBy, setGroupBy] = useState<(typeof GROUP_OPTIONS)[number]["id"]>("case_recipe");

  const filtered = useMemo(
    () =>
      rows.filter((row) => {
        if (caseId && row.case_id !== caseId) return false;
        if (category && row.category !== category) return false;
        if (style && row.style_id !== style) return false;
        if (template && row.template_id !== template) return false;
        if (label && `${row.label ?? ""}|${row.prompt_version ?? ""}` !== label) return false;
        if (mode && row.mode !== mode) return false;
        if (imageModel && row.image_model !== imageModel) return false;
        return true;
      }),
    [rows, caseId, category, style, template, label, mode, imageModel],
  );

  const grouped = useMemo(() => {
    const buckets = new Map<
      string,
      { overall: number[]; identity: number[]; commercial: number[]; hard: boolean[] }
    >();
    for (const row of filtered) {
      const key = groupKey(row, groupBy);
      const bucket = buckets.get(key) ?? {
        overall: [],
        identity: [],
        commercial: [],
        hard: [],
      };
      if (row.overall != null) bucket.overall.push(row.overall);
      if (row.identity != null) bucket.identity.push(row.identity);
      if (row.commercial != null) bucket.commercial.push(row.commercial);
      if (row.hard_failed != null) bucket.hard.push(row.hard_failed);
      buckets.set(key, bucket);
    }
    return [...buckets.entries()].map(([key, bucket]) => ({
      key,
      rated: bucket.overall.length,
      avg_overall: avg(bucket.overall),
      avg_identity: avg(bucket.identity),
      avg_commercial: avg(bucket.commercial),
      hard_fail_rate: bucket.hard.length
        ? Math.round((bucket.hard.filter(Boolean).length / bucket.hard.length) * 100) / 100
        : null,
    }));
  }, [filtered, groupBy]);

  const filters = [
    ["Case", caseId, setCaseId, unique(rows.map((row) => row.case_id))] as const,
    ["Category", category, setCategory, unique(rows.map((row) => row.category))] as const,
    ["Style", style, setStyle, unique(rows.map((row) => row.style_id))] as const,
    ["Template", template, setTemplate, unique(rows.map((row) => row.template_id))] as const,
    [
      "Label / prompt",
      label,
      setLabel,
      unique(rows.map((row) => `${row.label ?? ""}|${row.prompt_version ?? ""}`)),
    ] as const,
    ["Mode", mode, setMode, unique(rows.map((row) => row.mode))] as const,
    ["Image model", imageModel, setImageModel, unique(rows.map((row) => row.image_model))] as const,
  ];

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <p className="text-sm text-muted">
        <a href="/dev/creative-eval" className="underline">
          All runs
        </a>
        {" · "}
        <a href="/dev/creative-eval/compare" className="underline">
          Compare
        </a>
      </p>
      <h1 className="mb-2 text-3xl font-bold">Recipe summary</h1>
      <p className="mb-6 text-sm text-muted">
        Default grouping is case + recipe so clothing scores do not mix with food.
      </p>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {filters.map(([name, value, setter, options]) => (
          <label key={name} className="text-sm">
            <span className="text-muted">{name}</span>
            <select
              className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1"
              value={value}
              onChange={(event) => setter(event.target.value)}
            >
              <option value="">All</option>
              {options.map((option) => (
                <option key={option} value={option}>
                  {option.includes("|") ? option.replace("|", " / ") : option}
                </option>
              ))}
            </select>
          </label>
        ))}
        <label className="text-sm">
          <span className="text-muted">Group by</span>
          <select
            className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1"
            value={groupBy}
            onChange={(event) =>
              setGroupBy(event.target.value as (typeof GROUP_OPTIONS)[number]["id"])
            }
          >
            {GROUP_OPTIONS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {grouped.length === 0 ? (
        <p className="text-muted">No human ratings match these filters.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-muted">
              <th className="py-2">Group</th>
              <th>n</th>
              <th>Avg overall</th>
              <th>Avg identity</th>
              <th>Avg commercial</th>
              <th>QC hard-fail</th>
            </tr>
          </thead>
          <tbody>
            {grouped.map((row) => (
              <tr key={row.key} className="border-b border-border">
                <td className="py-2 font-medium">{row.key}</td>
                <td>{row.rated}</td>
                <td>{row.avg_overall ?? "—"}</td>
                <td>{row.avg_identity ?? "—"}</td>
                <td>{row.avg_commercial ?? "—"}</td>
                <td>{row.hard_fail_rate ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
