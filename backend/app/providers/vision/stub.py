from __future__ import annotations

import json

from app.providers.vision.base import (
    CampaignStrategy,
    CandidateQuality,
    ConceptCopy,
    ConceptIdentity,
    CreativeAgentContext,
    CreativeAgentResult,
    CreativeImage,
    LlmCallTrace,
    QualityContext,
    QualityReport,
    TextSafeArea,
    VisualPlan,
    llm_image_ref,
)
from app.providers.vision.prompts import (
    QUALITY_SYSTEM,
    creative_agent_system,
    creative_user_prompt,
    quality_user_prompt,
)

_ANGLES = (
    {
        "concept_title": "قهرمان محصول",
        "creative_angle": "clean commercial hero",
        "scene": "designed studio set with soft daylight",
        "composition": "product dominant with empty lower band",
        "camera": "slight three-quarter, eye level",
        "lighting": "soft key from camera left",
        "palette": "neutral warm commercial",
        "product_role": "hero object occupying most of the useful frame",
        "human_or_pose": None,
        "safe": "bottom",
        "prompt": (
            "Photograph this exact product as a 4:5 Instagram advertisement still. "
            "Place it as the clear hero on a designed commercial set with soft daylight, "
            "not a blank seamless. Keep silhouette, color, and graphics identical to the "
            "reference. Leave an empty lower band for later overlay type with no letters "
            "in the picture. Do not invent logos, extra SKUs, or readable text."
        ),
        "headline": "کیفیتی که فرقش حس می‌شه",
        "caption": "همین محصول، با کیفیت واقعی که از نزدیک حس می‌شود.",
        "story": "کیفیت را از نزدیک ببین.",
        "cta": "سفارش بده",
    },
    {
        "concept_title": "سبک زندگی",
        "creative_angle": "lifestyle environment",
        "scene": "lived-in interior with window light",
        "composition": "product integrated at a side table, off-center",
        "camera": "wider environmental view, product still readable",
        "lighting": "window light with gentle falloff",
        "palette": "warm interior tones",
        "product_role": "recognizable hero inside a real place",
        "human_or_pose": None,
        "safe": "upper-left",
        "prompt": (
            "Make a 4:5 lifestyle advertisement still of this exact product in a lived-in "
            "interior with window light. Keep the product identity faithful to the "
            "reference. Compose off-center with depth and an empty upper-left region for "
            "later overlay type. No invented text, logos, or extra product variants."
        ),
        "headline": "برای روزمره ساخته شده",
        "caption": "محصولی که در فضای واقعی زندگی می‌درخشد، نه فقط در استودیو.",
        "story": "برای روز تو آماده است.",
        "cta": "ببین و بخر",
    },
    {
        "concept_title": "نمایش پریمیوم",
        "creative_angle": "pedestal presentation",
        "scene": "museum-like plinth in a dark designed set",
        "composition": "low three-quarter honoring the plinth",
        "camera": "slightly low, product on a distinct stand",
        "lighting": "controlled spotlight with soft rim",
        "palette": "dark premium neutrals",
        "product_role": "elevated object on a designed pedestal",
        "human_or_pose": None,
        "safe": "top",
        "prompt": (
            "Create a 4:5 premium advertising still of this exact product on a designed "
            "plinth in a dark set. Preserve color, materials, and graphics from the "
            "reference. Leave a clear empty top region for overlay type. No readable "
            "text, no extra SKUs, no invented branding."
        ),
        "headline": "کیفیتی که دیده می‌شه",
        "caption": "نمایش تمیز و پریمیوم از همان محصولی که می‌فروشی.",
        "story": "یک نمایش تمیز از کیفیت.",
        "cta": "الان بگیر",
    },
)


def stub_creative_result(
    context: CreativeAgentContext,
    *,
    image: bytes,
    correction: str | None = None,
) -> CreativeAgentResult:
    count = context.requested_image_count
    chosen = _ANGLES[:count]
    template_id = context.template_id
    images = []
    for item in chosen:
        prompt = item["prompt"]
        if context.visual_instruction:
            prompt = (
                f"{prompt} Follow this seller direction: "
                f"{context.visual_instruction.strip()[:120]}"
            )[:800]
            if "4:5" not in prompt:
                prompt = f"4:5 still. {prompt}"[:800]
        images.append(
            CreativeImage(
                concept_title=item["concept_title"],
                creative_angle=item["creative_angle"],
                visual_plan=VisualPlan(
                    template_id=template_id,
                    scene=item["scene"],
                    composition=item["composition"],
                    camera=item["camera"],
                    lighting=item["lighting"],
                    palette=item["palette"],
                    product_role=item["product_role"],
                    human_or_pose=item["human_or_pose"],
                    text_safe_area=TextSafeArea(
                        position=item["safe"],
                        description=f"Empty {item['safe']} region for overlay type.",
                    ),
                ),
                identity=ConceptIdentity(
                    must_preserve=("keep silhouette", "keep major colors"),
                    must_not_generate=("no invented logos", "no extra SKUs"),
                ),
                final_prompt=prompt,
                copy=ConceptCopy(
                    on_image_headline=item["headline"],
                    on_image_secondary=None,
                    feed_caption=item["caption"],
                    story_text=item["story"],
                    cta=item["cta"],
                    hashtags=("#آفرین", "#محصول"),
                ),
            )
        )
    return CreativeAgentResult(
        product_summary=f"visible product: {context.product_name}",
        campaign_strategy=CampaignStrategy(
            core_message="کیفیت واقعی محصول را نشان بده",
            audience_takeaway="این همان محصول قابل اعتماد است",
            tone="commercial",
        ),
        images=tuple(images),
        llm_trace=LlmCallTrace(
            name="creative_agent",
            model="stub",
            system=creative_agent_system(count),
            user=creative_user_prompt(context, correction=correction),
            images=(llm_image_ref(image, "cleaned_reference"),),
            output=json.dumps(
                {
                    "product_summary": context.product_name,
                    "count": count,
                    "template_id": template_id,
                    "instruction": context.visual_instruction,
                },
                ensure_ascii=False,
            ),
        ),
    )


class StubCreativeAgent:
    name = "stub"
    model: str | None = None

    async def create_campaign(
        self,
        image: bytes,
        context: CreativeAgentContext,
        *,
        correction: str | None = None,
    ) -> CreativeAgentResult:
        return stub_creative_result(context, image=image, correction=correction)

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: QualityContext,
    ) -> QualityReport:
        rows = tuple(
            CandidateQuality(slot=index + 1, hard_failed=False)
            for index in range(len(candidates))
        )
        images = [llm_image_ref(reference, "cleaned_reference")]
        images.extend(
            llm_image_ref(frame, f"candidate_{index + 1}")
            for index, frame in enumerate(candidates)
        )
        return QualityReport(
            candidates=rows,
            llm_trace=LlmCallTrace(
                name="visual_quality",
                model="stub",
                system=QUALITY_SYSTEM,
                user=quality_user_prompt(context, len(candidates)),
                images=tuple(images),
                output=json.dumps(
                    {
                        "candidates": [
                            {"slot": item.slot, "hard_failed": item.hard_failed}
                            for item in rows
                        ]
                    }
                ),
            ),
        )
