"""
Compare Persian LLM output across models without touching production.

    uv run python -m scripts.eval_llm
    uv run python -m scripts.eval_llm --model openai/gpt-4.1-mini

Writes JSON under eval/out/. Requires OPENROUTER_API_KEY.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.content.context import CopyContext, PreviousConcept
from app.content.copy import CaptionSet, ReelConcept
from app.core.config import Settings, get_settings
from app.providers.llm.claims import find_unsupported_claims
from app.providers.llm.openrouter.client import OpenRouterClient
from app.providers.llm.openrouter.provider import OpenRouterContentProvider

BRIEFS_DIR = Path(__file__).resolve().parents[1] / "eval" / "briefs"
OUT_DIR = Path(__file__).resolve().parents[1] / "eval" / "out"
PERSIAN = re.compile(r"[\u0600-\u06FF]")
LATIN_WORD = re.compile(r"\b[A-Za-z]{3,}\b")


def load_briefs() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(BRIEFS_DIR.glob("*.json"))
    ]


def _context(brief: dict, **overrides: object) -> CopyContext:
    values = {
        "product_name": brief["product_name"],
        "description": brief.get("description"),
        "price_text": brief.get("price_text"),
        "benefit": brief.get("benefit"),
        "brand_name": brief.get("brand_name"),
        "audience": brief.get("audience"),
        "objective": brief["objective"],
        "style": brief["style"],
        "round": 0,
    }
    values.update(overrides)
    return CopyContext(**values)


def _claim_records(text: str, brief: dict) -> list[dict]:
    return [
        {"category": hit.category, "snippet": hit.snippet}
        for hit in find_unsupported_claims(text, brief)
    ]


def score_concepts(brief: dict, drafts: list) -> dict:
    names = [brief["product_name"]]
    if brief.get("brand_name"):
        names.append(brief["brand_name"])
    latin = []
    missing_name = []
    concept_blobs = []
    for draft in drafts:
        blob = f"{draft.title_fa} {draft.headline_fa} {draft.description_fa}"
        concept_blobs.append(blob)
        latin.extend(LATIN_WORD.findall(blob))
        for name in names:
            if name not in blob:
                missing_name.append({"concept": draft.title_fa, "name": name})
    claims = _claim_records("\n".join(concept_blobs), brief)
    return {
        "count": len(drafts),
        "valid_count": len(drafts) == 3,
        "persian_headlines": all(PERSIAN.search(d.headline_fa) for d in drafts),
        "name_preservation_misses": missing_name,
        "latin_words": sorted(set(latin)),
        "headline_lengths": [len(d.headline_fa) for d in drafts],
        "background_ids": [d.background_id for d in drafts],
        "unsupported_claims": claims,
        "unsupported_claim_count": len(claims),
        "rubric": {
            "natural_iranian_persian": None,
            "nimfaseleh": None,
            "cta_strength": None,
            "no_invented_facts": len(claims) == 0,
        },
        "concepts": [
            {
                "title_fa": d.title_fa,
                "headline_fa": d.headline_fa,
                "description_fa": d.description_fa,
                "visual_direction": d.visual_direction,
                "background_prompt": d.background_prompt,
            }
            for d in drafts
        ],
    }


def score_copy(brief: dict, captions: CaptionSet, stories: list[str], reel: ReelConcept) -> dict:
    blob = "\n".join(
        [
            captions.caption_short,
            captions.caption_friendly,
            captions.caption_persuasive,
            *stories,
            reel.hook_fa,
            *reel.scenes_fa,
            reel.cta_fa,
            reel.voiceover_fa,
        ]
    )
    claims = _claim_records(blob, brief)
    jargon = [
        word
        for word in ("UGC", "hook", "rhythmic", "cut")
        if re.search(rf"\b{word}\b", blob, re.IGNORECASE)
    ]
    return {
        "unsupported_claims": claims,
        "unsupported_claim_count": len(claims),
        "english_jargon": jargon,
        "captions": {
            "short": captions.caption_short,
            "friendly": captions.caption_friendly,
            "persuasive": captions.caption_persuasive,
        },
        "story_ideas": stories,
        "reel": reel.to_dict(),
    }


def score_regeneration(first: list, second: list) -> dict:
    first_titles = {draft.title_fa.strip() for draft in first}
    overlap = [draft.title_fa for draft in second if draft.title_fa.strip() in first_titles]
    return {
        "repeated_titles": overlap,
        "titles_are_new": len(overlap) == 0,
        "second_round": [
            {"title_fa": d.title_fa, "visual_direction": d.visual_direction}
            for d in second
        ],
    }


async def run(model: str) -> dict:
    base = get_settings()
    if not base.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    settings = Settings(
        content_provider="openrouter",
        openrouter_api_key=base.openrouter_api_key,
        llm_model=model,
        llm_base_url=base.llm_base_url,
        llm_timeout_seconds=60,
        llm_max_retries=1,
        llm_http_referer=base.llm_http_referer,
        llm_app_title=base.llm_app_title,
    )
    provider = OpenRouterContentProvider(OpenRouterClient(settings), settings)
    results = []
    for brief in load_briefs():
        ctx = _context(brief)
        drafts = await provider.build_concepts(ctx)
        row = {"brief_id": brief["id"], **score_concepts(brief, drafts)}

        captions = await provider.build_captions(ctx)
        stories = await provider.build_story_ideas(ctx)
        reel = await provider.build_reel_concept(ctx)
        row["copy"] = score_copy(brief, captions, stories, reel)

        if brief["id"] == "candle":
            previous = tuple(
                PreviousConcept(
                    title_fa=draft.title_fa,
                    description_fa=draft.description_fa,
                    visual_direction=draft.visual_direction,
                )
                for draft in drafts
            )
            second = await provider.build_concepts(
                _context(brief, round=1, previous_concepts=previous)
            )
            row["regeneration"] = score_regeneration(drafts, second)
            row["regeneration"].update(
                {
                    "unsupported_claims": _claim_records(
                        "\n".join(
                            f"{d.title_fa} {d.headline_fa} {d.description_fa}"
                            for d in second
                        ),
                        brief,
                    )
                }
            )

        results.append(row)
    return {
        "model": model,
        "generated_at": datetime.now(UTC).isoformat(),
        "briefs": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    settings = get_settings()
    model = args.model or settings.llm_model
    report = asyncio.run(run(model))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{model.replace('/', '_')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
