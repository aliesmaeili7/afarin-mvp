from datetime import UTC, datetime

from app.db.models import GenerationJob
from app.providers.llm import get_content_provider
from app.providers.llm.base import ContentProvider, LlmUsage


def apply_usage(job: GenerationJob, provider: ContentProvider | None = None) -> None:
    """Copy the last LLM call onto the job. Stub leaves tokens/cost null."""
    active = provider or get_content_provider()
    job.provider = active.name
    job.model = active.model
    usage = active.consume_usage()
    if usage is None:
        return
    _write_usage(job, usage)


def _write_usage(job: GenerationJob, usage: LlmUsage) -> None:
    job.prompt_tokens = usage.prompt_tokens
    job.completion_tokens = usage.completion_tokens
    job.latency_ms = usage.latency_ms
    job.actual_cost_usd = usage.cost_usd
    if usage.model:
        job.model = usage.model


def mark_failed(job: GenerationJob, error: Exception) -> None:
    job.status = "failed"
    job.completed_at = datetime.now(UTC)
    job.error_message = str(error)[:2000]
    apply_usage(job)


def mark_succeeded(job: GenerationJob, output: dict | None = None) -> None:
    job.status = "succeeded"
    job.completed_at = datetime.now(UTC)
    if output is not None:
        job.output_json = output
    apply_usage(job)
