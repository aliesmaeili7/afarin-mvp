import { describe, expect, it } from "vitest";
import {
  computeGenerationProgress,
  GENERATION_STAGES,
  TOTAL_GENERATION_MS,
} from "./generation";

describe("computeGenerationProgress", () => {
  it("uses the unified creative-agent stages", () => {
    expect(GENERATION_STAGES.map((stage) => stage.stage)).toEqual([
      "planning",
      "visual",
      "finalizing",
    ]);
  });

  it("starts on the first stage", () => {
    const progress = computeGenerationProgress(0);
    expect(progress.stage).toBe(GENERATION_STAGES[0].stage);
    expect(progress.done).toBe(false);
    expect(progress.percent).toBe(0);
  });

  it("walks the stages in order as time passes", () => {
    let elapsed = 0;
    GENERATION_STAGES.forEach((stage) => {
      const midpoint = elapsed + stage.duration_ms / 2;
      expect(computeGenerationProgress(midpoint).stage).toBe(stage.stage);
      elapsed += stage.duration_ms;
    });
    expect(elapsed).toBe(TOTAL_GENERATION_MS);
  });

  it("never reports 100 percent before the work is finished", () => {
    const progress = computeGenerationProgress(TOTAL_GENERATION_MS - 1);
    expect(progress.done).toBe(false);
    expect(progress.percent).toBeLessThanOrEqual(99);
  });

  it("completes once the total duration has elapsed", () => {
    const progress = computeGenerationProgress(TOTAL_GENERATION_MS);
    expect(progress.done).toBe(true);
    expect(progress.percent).toBe(100);
  });

  it("stays complete for a tab that was closed for a long time", () => {
    const progress = computeGenerationProgress(TOTAL_GENERATION_MS * 20);
    expect(progress.done).toBe(true);
  });

  it("treats a negative clock skew as the beginning", () => {
    expect(computeGenerationProgress(-5000).percent).toBe(0);
  });
});
