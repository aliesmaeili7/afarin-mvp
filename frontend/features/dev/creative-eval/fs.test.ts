import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { runDir, safeFile } from "./fs";

describe("creative eval path safety", () => {
  it("rejects traversal in run ids", () => {
    expect(runDir("../secret")).toBeNull();
    expect(runDir("ok-run")).toContain("creative_runs");
  });

  it("keeps files inside the run directory", () => {
    const dest = safeFile("2026-08-21_001_sweatshirt_01", [
      "recipes",
      "01_anime__illustrated_scene",
      "candidate-1.jpg",
    ]);
    expect(dest).toBe(
      join(
        process.cwd(),
        "..",
        "backend",
        "eval",
        "creative_runs",
        "2026-08-21_001_sweatshirt_01",
        "recipes",
        "01_anime__illustrated_scene",
        "candidate-1.jpg",
      ),
    );
    expect(safeFile("run", ["..", "secrets.json"])).toBeNull();
  });
});
