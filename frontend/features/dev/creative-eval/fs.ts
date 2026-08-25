import { isAbsolute, join, normalize, relative, sep } from "node:path";
import { existsSync } from "node:fs";
import { readdir, readFile, writeFile } from "node:fs/promises";
import type { SummaryObservation } from "./types";

export function runsRoot(): string {
  return join(process.cwd(), "..", "backend", "eval", "creative_runs");
}

export function isDevEvalEnabled(): boolean {
  return process.env.NODE_ENV !== "production";
}

export function runDir(runId: string): string | null {
  if (!runId || runId.includes("..") || runId.includes("/") || runId.includes("\\")) {
    return null;
  }
  const dest = join(runsRoot(), runId);
  const rel = relative(runsRoot(), dest);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    return null;
  }
  return dest;
}

export function safeFile(runId: string, parts: string[]): string | null {
  const root = runDir(runId);
  if (!root) {
    return null;
  }
  const dest = normalize(join(root, ...parts));
  const rel = relative(root, dest);
  if (rel.startsWith("..") || isAbsolute(rel) || rel.split(sep).includes("..")) {
    return null;
  }
  return dest;
}

export async function listRuns(): Promise<Record<string, unknown>[]> {
  const root = runsRoot();
  if (!existsSync(root)) {
    return [];
  }
  const names = await readdir(root, { withFileTypes: true });
  const rows: Record<string, unknown>[] = [];
  for (const entry of names.reverse()) {
    if (!entry.isDirectory() || entry.name.startsWith("_")) {
      continue;
    }
    try {
      const raw = await readFile(join(root, entry.name, "run_meta.json"), "utf8");
      const meta = JSON.parse(raw) as Record<string, unknown>;
      try {
        const timingRaw = await readFile(join(root, entry.name, "timing.json"), "utf8");
        const timing = JSON.parse(timingRaw) as Record<string, unknown>;
        meta.timing = timing;
        meta.wall_time_ms = timing.wall_time_ms;
        meta.timing_summary = timing.summary;
      } catch {
        /* old runs omit timing */
      }
      rows.push(meta);
    } catch {
      rows.push({ run_id: entry.name });
    }
  }
  return rows;
}

export async function listBatches(): Promise<Record<string, unknown>[]> {
  const root = join(runsRoot(), "_batches");
  if (!existsSync(root)) {
    return [];
  }
  const names = await readdir(root);
  const rows: Record<string, unknown>[] = [];
  for (const name of names.sort().reverse()) {
    if (!name.endsWith(".json")) {
      continue;
    }
    try {
      const raw = await readFile(join(root, name), "utf8");
      rows.push({ file: name, ...(JSON.parse(raw) as Record<string, unknown>) });
    } catch {
      rows.push({ file: name });
    }
  }
  return rows;
}

export async function readJson(
  runId: string,
  relativePath: string,
): Promise<unknown | null> {
  const dest = safeFile(runId, relativePath.split("/"));
  if (!dest || !existsSync(dest)) {
    return null;
  }
  return JSON.parse(await readFile(dest, "utf8")) as unknown;
}

export async function writeJson(
  runId: string,
  relativePath: string,
  payload: unknown,
): Promise<void> {
  const dest = safeFile(runId, relativePath.split("/"));
  if (!dest) {
    throw new Error("invalid run path");
  }
  await writeFile(dest, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function parseRecipeFolder(folder: string): { style_id: string; template_id: string } {
  const rest = folder.replace(/^\d+_/, "");
  const [style_id, template_id] = rest.split("__");
  return { style_id: style_id || folder, template_id: template_id || "" };
}

export async function listObservations(): Promise<SummaryObservation[]> {
  const root = runsRoot();
  if (!existsSync(root)) {
    return [];
  }
  const names = await readdir(root, { withFileTypes: true });
  const rows: SummaryObservation[] = [];
  for (const entry of names) {
    if (!entry.isDirectory() || entry.name.startsWith("_")) {
      continue;
    }
    const ratingsPath = join(root, entry.name, "ratings.json");
    if (!existsSync(ratingsPath)) {
      continue;
    }
    let meta: Record<string, unknown> = { run_id: entry.name };
    try {
      meta = JSON.parse(await readFile(join(root, entry.name, "run_meta.json"), "utf8"));
    } catch {
      /* old or incomplete run */
    }
    const ratings = JSON.parse(await readFile(ratingsPath, "utf8")) as {
      candidates?: Record<string, { overall?: number; identity?: number; commercial?: number }>;
    };
    for (const [key, row] of Object.entries(ratings.candidates ?? {})) {
      const recipeKey = key.includes(":") ? key.slice(0, key.lastIndexOf(":")) : key;
      const slot = Number(key.split(":").at(-1) ?? "1");
      const recipePath = join(root, entry.name, "recipes", recipeKey, "recipe.json");
      let style_id = "";
      let template_id = "";
      if (existsSync(recipePath)) {
        const recipe = JSON.parse(await readFile(recipePath, "utf8")) as {
          style_id?: string;
          template_id?: string;
        };
        style_id = String(recipe.style_id ?? "");
        template_id = String(recipe.template_id ?? "");
      } else {
        const parsed = parseRecipeFolder(recipeKey);
        style_id = parsed.style_id;
        template_id = parsed.template_id;
      }
      let hard_failed: boolean | null = null;
      const qualityPath = join(root, entry.name, "recipes", recipeKey, "quality.json");
      if (existsSync(qualityPath)) {
        const quality = JSON.parse(await readFile(qualityPath, "utf8")) as {
          candidates?: { slot: number; hard_failed?: boolean }[];
        };
        const hit = quality.candidates?.find((item) => item.slot === slot);
        if (hit) {
          hard_failed = Boolean(hit.hard_failed);
        }
      }
      rows.push({
        run_id: String(meta.run_id ?? entry.name),
        case_id: String(meta.case_id ?? ""),
        category: typeof meta.category === "string" ? meta.category : null,
        style_id,
        template_id,
        recipe: style_id && template_id ? `${style_id}:${template_id}` : recipeKey,
        label: typeof meta.label === "string" ? meta.label : null,
        prompt_version: typeof meta.prompt_version === "string" ? meta.prompt_version : null,
        mode: String(meta.mode ?? ""),
        image_model: typeof meta.image_model === "string" ? meta.image_model : null,
        overall: typeof row.overall === "number" ? row.overall : null,
        identity: typeof row.identity === "number" ? row.identity : null,
        commercial: typeof row.commercial === "number" ? row.commercial : null,
        hard_failed,
      });
    }
  }
  return rows;
}

export async function recipeSummaries(): Promise<Record<string, unknown>[]> {
  const observations = await listObservations();
  const buckets = new Map<
    string,
    { recipe: string; n: number; overall: number; identity: number; commercial: number; hardFail: number; hardFailN: number }
  >();
  for (const row of observations) {
    const bucket = buckets.get(row.recipe) ?? {
      recipe: row.recipe,
      n: 0,
      overall: 0,
      identity: 0,
      commercial: 0,
      hardFail: 0,
      hardFailN: 0,
    };
    if (row.overall != null) {
      bucket.n += 1;
      bucket.overall += row.overall;
      if (row.identity != null) {
        bucket.identity += row.identity;
      }
      if (row.commercial != null) {
        bucket.commercial += row.commercial;
      }
    }
    if (row.hard_failed != null) {
      bucket.hardFailN += 1;
      if (row.hard_failed) {
        bucket.hardFail += 1;
      }
    }
    buckets.set(row.recipe, bucket);
  }
  return [...buckets.values()].map((bucket) => ({
    recipe: bucket.recipe,
    rated: bucket.n,
    avg_overall: bucket.n ? Math.round((bucket.overall / bucket.n) * 100) / 100 : null,
    avg_identity: bucket.n ? Math.round((bucket.identity / bucket.n) * 100) / 100 : null,
    avg_commercial: bucket.n ? Math.round((bucket.commercial / bucket.n) * 100) / 100 : null,
    hard_fail_rate: bucket.hardFailN
      ? Math.round((bucket.hardFail / bucket.hardFailN) * 100) / 100
      : null,
  }));
}

export async function readRunBundle(runId: string): Promise<Record<string, unknown> | null> {
  const root = runDir(runId);
  if (!root || !existsSync(root)) {
    return null;
  }
  const meta = (await readJson(runId, "run_meta.json")) as Record<string, unknown> | null;
  if (!meta) {
    return null;
  }
  const recipesDir = join(root, "recipes");
  const recipes: Record<string, unknown>[] = [];
  if (existsSync(recipesDir)) {
    const folders = await readdir(recipesDir, { withFileTypes: true });
    for (const folder of folders.sort((a, b) => a.name.localeCompare(b.name))) {
      if (!folder.isDirectory()) {
        continue;
      }
      const base = join(recipesDir, folder.name);
      const readOptional = async (name: string) => {
        const path = join(base, name);
        if (!existsSync(path)) {
          return null;
        }
        if (name.endsWith(".json")) {
          return JSON.parse(await readFile(path, "utf8")) as unknown;
        }
        return await readFile(path, "utf8");
      };
      const files = existsSync(base)
        ? (await readdir(base)).filter((name) => /\.(jpg|jpeg|png|txt|json)$/i.test(name))
        : [];
      recipes.push({
        folder: folder.name,
        recipe: await readOptional("recipe.json"),
        direction: await readOptional("direction.json"),
        prompt: await readOptional("effective_prompt.txt"),
        promptJson: await readOptional("prompt.json"),
        quality: await readOptional("quality.json"),
        metrics: await readOptional("metrics.json"),
        error: await readOptional("error.json"),
        llmCalls: await readOptional("llm_calls.json"),
        imageRequests: await readOptional("image_requests.json"),
        architect: await readOptional("architect.json"),
        validation: await readOptional("validation.json"),
        files,
      });
    }
  }
  return {
    meta,
    brief: await readJson(runId, "effective_brief.json"),
    director: await readJson(runId, "director_output.json"),
    directorLlmCalls: await readJson(runId, "llm_calls.json"),
    cost: await readJson(runId, "cost.json"),
    ratings: (await readJson(runId, "ratings.json")) ?? { candidates: {}, director: {} },
    recipes,
    timing: await readJson(runId, "timing.json"),
  };
}
