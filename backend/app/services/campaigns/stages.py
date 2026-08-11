"""
The generation progress model (spec §12).

A faithful port of frontend/lib/api/mock/generation.ts. Progress is derived from
the job's `started_at` rather than held in a timer, so a refresh, a backgrounded
tab or a reopened browser all resume at the correct stage — and generation
survives the seller closing the page, which the spec requires.

Phase 2 runs no providers, so the elapsed time is simulated. Keeping the same
total as Phase 1 means the progress screen behaves identically; setting
GENERATION_SIMULATED_MS to 0 makes it instant for tests.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StageDefinition:
    stage: str
    weight: float
    message_fa: str


# Weights, not durations, so the total is configurable without reshaping the
# relative length of each stage.
STAGES: tuple[StageDefinition, ...] = (
    StageDefinition("planning", 2600, "در حال آماده کردن ایده تبلیغ…"),
    StageDefinition("visual", 4800, "در حال ساخت تصویر محصول…"),
    StageDefinition("captions", 2800, "در حال نوشتن کپشن‌ها…"),
    StageDefinition("story", 2000, "در حال آماده کردن استوری…"),
    StageDefinition("finalizing", 1600, "تقریباً آماده‌ست…"),
)

TOTAL_WEIGHT = sum(stage.weight for stage in STAGES)


@dataclass(frozen=True, slots=True)
class Progress:
    stage: str
    stage_index: int
    percent: int
    message_fa: str
    done: bool


def compute_progress(elapsed_ms: float, total_ms: int) -> Progress:
    last = STAGES[-1]

    if total_ms <= 0 or elapsed_ms >= total_ms:
        return Progress(last.stage, len(STAGES) - 1, 100, last.message_fa, True)

    elapsed = max(0.0, elapsed_ms)
    consumed = 0.0
    for index, definition in enumerate(STAGES):
        duration = definition.weight / TOTAL_WEIGHT * total_ms
        if elapsed < consumed + duration:
            # Held at 99 so the bar never claims completion before the rows exist.
            percent = min(99, round(elapsed / total_ms * 100))
            return Progress(
                definition.stage, index, percent, definition.message_fa, False
            )
        consumed += duration

    return Progress(last.stage, len(STAGES) - 1, 99, last.message_fa, False)
