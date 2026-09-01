"""
The generation progress model (spec §12).

Stages match the Unified Creative Agent path: one idea pass, then Seedream
images, then package assembly. For stub/theatre runs, progress is derived from
elapsed time. Live image jobs persist the current stage on the job row so the
status poller can advance while Seedream is still running.
"""

from dataclasses import dataclass

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import GenerationJob


@dataclass(frozen=True, slots=True)
class StageDefinition:
    stage: str
    weight: float
    message_fa: str
    percent: int


STAGES: tuple[StageDefinition, ...] = (
    StageDefinition("planning", 2600, "در حال طراحی تبلیغ…", 20),
    StageDefinition("visual", 8000, "در حال ساخت تصویر…", 55),
    StageDefinition("finalizing", 1600, "تقریباً آماده‌ست…", 90),
)

TOTAL_WEIGHT = sum(stage.weight for stage in STAGES)
_BY_STAGE = {item.stage: item for item in STAGES}


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


def progress_for_stage(stage: str | None) -> Progress | None:
    if not stage:
        return None
    match = _BY_STAGE.get(stage)
    if match is None:
        return None
    index = STAGES.index(match)
    return Progress(match.stage, index, match.percent, match.message_fa, False)


def job_stage(job: GenerationJob | None) -> str | None:
    if job is None:
        return None
    value = (job.input_json or {}).get("stage")
    return value if isinstance(value, str) else None


def set_job_stage(job: GenerationJob, stage: str) -> None:
    payload = dict(job.input_json or {})
    payload["stage"] = stage
    job.input_json = payload
    flag_modified(job, "input_json")
