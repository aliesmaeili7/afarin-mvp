import type { GenerationStage } from "@/types/domain";

/**
 * The mocked generation pipeline (spec §12).
 *
 * Progress is derived from `generation_started_at` rather than kept in a timer,
 * so a refresh, a backgrounded tab or a reopened browser all resume at the
 * correct stage exactly like polling a real job queue would.
 */
export interface StageDefinition {
  stage: GenerationStage;
  duration_ms: number;
  message_fa: string;
}

export const GENERATION_STAGES: readonly StageDefinition[] = [
  {
    stage: "planning",
    duration_ms: 2600,
    message_fa: "در حال آماده کردن ایده تبلیغ…",
  },
  {
    stage: "visual",
    duration_ms: 4800,
    message_fa: "در حال ساخت تصویر محصول…",
  },
  {
    stage: "captions",
    duration_ms: 2800,
    message_fa: "در حال نوشتن کپشن‌ها…",
  },
  {
    stage: "story",
    duration_ms: 2000,
    message_fa: "در حال آماده کردن استوری…",
  },
  {
    stage: "finalizing",
    duration_ms: 1600,
    message_fa: "تقریباً آماده‌ست…",
  },
] as const;

export const TOTAL_GENERATION_MS = GENERATION_STAGES.reduce(
  (total, stage) => total + stage.duration_ms,
  0,
);

export interface GenerationProgress {
  stage: GenerationStage;
  stage_index: number;
  percent: number;
  message_fa: string;
  done: boolean;
}

export function computeGenerationProgress(
  elapsedMs: number,
): GenerationProgress {
  const elapsed = Math.max(0, elapsedMs);

  if (elapsed >= TOTAL_GENERATION_MS) {
    const last = GENERATION_STAGES[GENERATION_STAGES.length - 1];
    return {
      stage: last.stage,
      stage_index: GENERATION_STAGES.length - 1,
      percent: 100,
      message_fa: last.message_fa,
      done: true,
    };
  }

  let consumed = 0;
  for (let index = 0; index < GENERATION_STAGES.length; index += 1) {
    const definition = GENERATION_STAGES[index];
    if (elapsed < consumed + definition.duration_ms) {
      // Hold at 99 so the bar never claims completion before the data exists.
      const percent = Math.min(
        99,
        Math.round((elapsed / TOTAL_GENERATION_MS) * 100),
      );
      return {
        stage: definition.stage,
        stage_index: index,
        percent,
        message_fa: definition.message_fa,
        done: false,
      };
    }
    consumed += definition.duration_ms;
  }

  const last = GENERATION_STAGES[GENERATION_STAGES.length - 1];
  return {
    stage: last.stage,
    stage_index: GENERATION_STAGES.length - 1,
    percent: 99,
    message_fa: last.message_fa,
    done: false,
  };
}
