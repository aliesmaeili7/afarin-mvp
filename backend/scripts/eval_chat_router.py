"""
Live Orchestrator routing eval. Does not generate images.

    uv run python -m scripts.eval_chat_router

Requires OPENROUTER_API_KEY. Skips silently if CONTENT_PROVIDER is stub and
no key is set. Writes JSON under eval/out/chat_router/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.orchestrator.context import BoundedChatContext
from app.services.orchestrator.provider import OpenRouterOrchestratorProvider

OUT_DIR = Path(__file__).resolve().parents[1] / "eval" / "out" / "chat_router"

CASES = [
    {"id": "edu_fa", "text": "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن."},
    {"id": "ad_mixed", "text": "یه minimal ad بساز"},
    {"id": "caption_fa", "text": "برای Instagram کپشن بده"},
    {"id": "ad_en", "text": "Make an ad for this."},
    {"id": "reply_en", "text": "Please answer in English: برای این کپشن بده"},
    {"id": "reply_fa", "text": "فارسی جواب بده: Make an ad"},
    {"id": "image_fa", "text": "یه تصویر از یک فنجان چای بساز"},
    {"id": "music", "text": "یه آهنگ بساز"},
    {"id": "vague", "text": "یه چیزی برام بساز"},
]


def _context(text: str) -> BoundedChatContext:
    return BoundedChatContext(
        conversation_id=uuid.uuid4(),
        latest_user_text=text,
        latest_user_message_id=uuid.uuid4(),
        recent_messages=[{"role": "user", "content": text, "language": "fa"}],
        recent_artifacts=[],
    )


async def run() -> dict:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is empty")
    provider = OpenRouterOrchestratorProvider()
    rows = []
    for case in CASES:
        decision = await provider.complete(_context(case["text"]))
        rows.append(
            {
                "id": case["id"],
                "text": case["text"],
                "route": decision.route,
                "reply_language": decision.reply_language,
                "artifact_language": decision.artifact_language,
                "needs_clarification": decision.needs_clarification,
            }
        )
        print(f"{case['id']:12} {decision.route:16} {decision.reply_language}")
    return {
        "model": settings.chat_orchestrator_model_resolved,
        "generated_at": datetime.now(UTC).isoformat(),
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="")
    args = parser.parse_args()
    if args.model.strip():
        os.environ["CHAT_ORCHESTRATOR_MODEL"] = args.model.strip()
        get_settings.cache_clear()
    payload = asyncio.run(run())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "latest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
