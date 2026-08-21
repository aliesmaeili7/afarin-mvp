import { isAbsolute, join, normalize, relative, sep } from "node:path";
import { existsSync } from "node:fs";
import { readdir, readFile, writeFile } from "node:fs/promises";

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
    if (!entry.isDirectory()) {
      continue;
    }
    try {
      const raw = await readFile(join(root, entry.name, "run_meta.json"), "utf8");
      rows.push(JSON.parse(raw) as Record<string, unknown>);
    } catch {
      rows.push({ run_id: entry.name });
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

export async function recipeSummaries(): Promise<Record<string, unknown>[]> {
  const root = runsRoot();
  if (!existsSync(root)) {
    return [];
  }
  const names = await readdir(root, { withFileTypes: true });
  type Bucket = {
    recipe: string;
    n: number;
    overall: number;
    identity: number;
    commercial: number;
    hardFail: number;
    hardFailN: number;
  };
  const buckets = new Map<string, Bucket>();
  for (const entry of names) {
    if (!entry.isDirectory()) {
      continue;
    }
    const ratingsPath = join(root, entry.name, "ratings.json");
    if (!existsSync(ratingsPath)) {
      continue;
    }
    const ratings = JSON.parse(await readFile(ratingsPath, "utf8")) as {
      candidates?: Record<string, { overall?: number; identity?: number; commercial?: number }>;
    };
    for (const [key, row] of Object.entries(ratings.candidates ?? {})) {
      const recipeKey = key.includes(":") ? key.slice(0, key.lastIndexOf(":")) : key;
      const bucket = buckets.get(recipeKey) ?? {
        recipe: recipeKey,
        n: 0,
        overall: 0,
        identity: 0,
        commercial: 0,
        hardFail: 0,
        hardFailN: 0,
      };
      if (typeof row.overall === "number") {
        bucket.n += 1;
        bucket.overall += row.overall;
        if (typeof row.identity === "number") {
          bucket.identity += row.identity;
        }
        if (typeof row.commercial === "number") {
          bucket.commercial += row.commercial;
        }
      }
      const slot = Number(key.split(":").at(-1) ?? "1");
      const qualityPath = join(root, entry.name, "recipes", recipeKey, "quality.json");
      if (existsSync(qualityPath)) {
        const quality = JSON.parse(await readFile(qualityPath, "utf8")) as {
          candidates?: { slot: number; hard_failed?: boolean }[];
        };
        for (const item of quality.candidates ?? []) {
          if (item.slot === slot) {
            bucket.hardFailN += 1;
            if (item.hard_failed) {
              bucket.hardFail += 1;
            }
          }
        }
      }
      buckets.set(recipeKey, bucket);
    }
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
        files,
      });
    }
  }
  return {
    meta,
    brief: await readJson(runId, "effective_brief.json"),
    director: await readJson(runId, "director_output.json"),
    cost: await readJson(runId, "cost.json"),
    ratings: (await readJson(runId, "ratings.json")) ?? { candidates: {}, director: {} },
    recipes,
  };
}
