from __future__ import annotations

import json

from app.content.visual_catalog import compatibility
from app.providers.vision.base import (
    ArchitectCandidate,
    ArchitectComposition,
    ArchitectContext,
    CampaignDirection,
    CandidateQuality,
    CLEAN_ANALYSIS,
    IdentityFeature,
    InputQuality,
    LlmCallTrace,
    PlannerContext,
    PlannerResult,
    PromptArchitectResult,
    QualityReport,
    ReferenceAnalysis,
    llm_image_ref,
)
from app.providers.vision.prompts import (
    ARCHITECT_SYSTEM,
    QUALITY_SYSTEM,
    architect_user_prompt,
    plan_user_prompt,
    planner_system,
    quality_user_prompt,
)


def _direction(
    *,
    title_fa: str,
    description_fa: str,
    angle: str,
    headline_fa: str,
    visual_direction: str,
    style_id: str,
    template_id: str,
    identity_constraints: tuple[str, ...],
    image_direction: str,
    background_prompt: str,
    text_safe_area: str,
) -> CampaignDirection:
    return CampaignDirection(
        title_fa=title_fa,
        description_fa=description_fa,
        angle=angle,
        headline_fa=headline_fa,
        visual_direction=visual_direction,
        style_id=style_id,
        template_id=template_id,
        identity_constraints=identity_constraints,
        image_direction=image_direction,
        background_prompt=background_prompt,
        text_safe_area=text_safe_area,
        compatibility=compatibility(style_id, template_id),
    )


SMART_DIRECTIONS = (
    _direction(
        title_fa="واقعی و واضح",
        description_fa="محصول در مرکز، نور استودیویی، مناسب فروش.",
        angle="editorial hero",
        headline_fa="کیفیتی که فرقش حس می‌شه",
        visual_direction="نور استودیویی نرم، محصول واضح در مرکز",
        style_id="photoreal_commercial",
        template_id="hero_product",
        identity_constraints=("keep major colors", "keep silhouette"),
        image_direction="clean studio hero, soft key light, product centered",
        background_prompt="clean light seamless backdrop, soft natural shadow, no text",
        text_safe_area="bottom",
    ),
    _direction(
        title_fa="در حال استفاده",
        description_fa="یک نفر محصول را طبیعی استفاده می‌کند.",
        angle="lifestyle use",
        headline_fa="برای روزمره ساخته شده",
        visual_direction="استفاده واقعی از محصول",
        style_id="photoreal_commercial",
        template_id="model_using",
        identity_constraints=("keep major colors", "keep graphic identity"),
        image_direction="person using the product naturally, product clearly visible",
        background_prompt="soft daylight interior, no product, no text",
        text_safe_area="bottom",
    ),
    _direction(
        title_fa="روی پایه",
        description_fa="نمایش پریمیوم روی استند طراحی‌شده.",
        angle="pedestal presentation",
        headline_fa="کیفیتی که دیده می‌شه",
        visual_direction="محصول روی پایه با نور کنترل‌شده",
        style_id="photoreal_commercial",
        template_id="product_pedestal",
        identity_constraints=("keep silhouette", "keep distinctive graphics"),
        image_direction="product on a designed plinth, museum-like set",
        background_prompt="simple designed set around an empty plinth, no text",
        text_safe_area="top",
    ),
)

ALT_DIRECTIONS = (
    _direction(
        title_fa="ادیتوریال مد",
        description_fa="حس مجله، نور سینمایی، محصول آشنا.",
        angle="fashion editorial",
        headline_fa="برای دیده شدن ساخته شده",
        visual_direction="ژست و نور مجله‌ای",
        style_id="fashion_editorial",
        template_id="magazine_cover",
        identity_constraints=("keep major colors", "keep silhouette"),
        image_direction="fashion magazine cover still, cinematic rim light",
        background_prompt="editorial studio cyclorama, soft cinematic light, no text",
        text_safe_area="top",
    ),
    _direction(
        title_fa="آبرنگ آرام",
        description_fa="نقاشی ملایم با فضای خالی برای متن.",
        angle="watercolor story",
        headline_fa="نرم، ساده، ماندگار",
        visual_direction="بافت آبرنگ و کاغذ مرطوب",
        style_id="watercolor_illustration",
        template_id="product_with_props",
        identity_constraints=("keep major colors",),
        image_direction="watercolor still life of the product with relevant props",
        background_prompt="wet paper watercolor wash, empty, no text",
        text_safe_area="bottom",
    ),
    _direction(
        title_fa="نئون شبانه",
        description_fa="شب شهری و نور نئون، محصول درخشان.",
        angle="neon night",
        headline_fa="شب مال توست",
        visual_direction="کنتراست نئون در شب شهر",
        style_id="neon",
        template_id="cinematic_environment",
        identity_constraints=("keep silhouette", "keep distinctive graphics"),
        image_direction="neon night street around the product",
        background_prompt="empty neon alley, wet asphalt reflections, no text",
        text_safe_area="bottom",
    ),
)


class StubVisualPlanner:
    name = "stub"
    model: str | None = None

    async def plan_directions(
        self,
        image: bytes,
        context: PlannerContext,
        *,
        original: bytes | None = None,
    ) -> PlannerResult:
        directions = (
            ALT_DIRECTIONS if context.previous_directions else SMART_DIRECTIONS
        )
        images = [llm_image_ref(image, "approved_crop")]
        user = plan_user_prompt(context)
        if original and original != image:
            images.append(llm_image_ref(original, "original_upload"))
            user = (
                "Image 1 = APPROVED CROP. Image 2 = ORIGINAL UPLOAD (may contain UI).\n"
                + user
            )
        return PlannerResult(
            product_visual_analysis="visible product on a simple background",
            product_type="product",
            visual_identity=("visible product",),
            identity_constraints=("keep major colors", "keep silhouette"),
            unsuitable_style_ids=(),
            unsuitable_template_ids=(),
            input_quality=InputQuality("ok"),
            directions=directions,
            forbidden_claims=(),
            reference_analysis=CLEAN_ANALYSIS,
            llm_trace=LlmCallTrace(
                name="creative_director",
                model="stub",
                system=planner_system(),
                user=user,
                images=tuple(images),
                output=json.dumps(
                    {
                        "product_visual_analysis": "visible product on a simple background",
                        "product_type": "product",
                        "directions": [
                            {
                                "style_id": item.style_id,
                                "template_id": item.template_id,
                                "title_fa": item.title_fa,
                            }
                            for item in directions
                        ],
                    },
                    ensure_ascii=False,
                ),
            ),
        )

    async def check_input_quality(
        self, image: bytes, context: PlannerContext
    ) -> InputQuality:
        del image, context
        return InputQuality("ok")

    async def score_candidates(
        self,
        reference: bytes,
        candidates: tuple[bytes, ...],
        context: PlannerContext,
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


def stub_architect_result() -> PromptArchitectResult:
    def candidate(
        slot: int,
        intention: str,
        camera: str,
        position: str,
        environment: str,
        prompt: str,
    ) -> ArchitectCandidate:
        return ArchitectCandidate(
            slot=slot,
            intention=intention,
            composition=ArchitectComposition(
                camera=camera,
                product_scale="product occupies about 55 percent of the frame",
                product_position=position,
                human_or_pose="",
                foreground="simple supporting surface",
                background="designed environment, no UI",
                environment=environment,
                depth="clear foreground midground background",
                text_safe_area="empty bottom band for Persian overlay",
            ),
            lighting="controlled commercial key light",
            palette="product-true colors",
            relevant_props=("one category-relevant prop",),
            must_preserve=("silhouette", "major colors"),
            must_avoid=("readable text", "Instagram UI"),
            image_prompt=prompt,
        )

    return PromptArchitectResult(
        reference_summary="visible seller product on a clean crop",
        identity_priority=(
            IdentityFeature("silhouette", "critical"),
            IdentityFeature("major colors", "critical"),
        ),
        art_direction={
            "visual_thesis": "clear commercial hero of this exact product",
            "product_role": "the single advertised SKU",
            "style_execution": "selected style made visible in materials and light",
            "template_execution": "selected template made visible in structure",
            "palette_strategy": "preserve product color",
            "typography_safe_area": "bottom empty band",
        },
        candidates=(
            candidate(
                1,
                "safe",
                "straight-on commercial camera, eye-level",
                "slightly off-center hero",
                "simple designed set",
                "safe commercial execution of the selected style and template, "
                "this exact product dominant, designed environment, empty type band",
            ),
            candidate(
                2,
                "editorial",
                "three-quarter camera, lower angle",
                "asymmetric placement",
                "richer set with depth",
                "editorial composition of the same style and template, "
                "asymmetric placement, deeper environment, product still dominant",
            ),
            candidate(
                3,
                "bold",
                "dramatic close three-quarter, strong geometry",
                "dynamic diagonal placement",
                "bold environmental interaction",
                "boldest reading of the same style and template, "
                "structural geometry change, environmental interaction, same product",
            ),
        ),
    )


class StubPromptArchitect:
    name = "stub"
    model: str | None = None

    async def plan_candidates(
        self,
        cleaned: bytes,
        context: ArchitectContext,
        *,
        original: bytes | None = None,
    ) -> PromptArchitectResult:
        style_id = str(context.recipe.get("style_id") or "photoreal_commercial")
        template_id = str(context.recipe.get("template_id") or "hero_product")
        result = stub_architect_result()
        tagged = []
        for item in result.candidates:
            tagged.append(
                ArchitectCandidate(
                    slot=item.slot,
                    intention=item.intention,
                    composition=item.composition,
                    lighting=item.lighting,
                    palette=item.palette,
                    relevant_props=item.relevant_props,
                    must_preserve=item.must_preserve,
                    must_avoid=item.must_avoid,
                    image_prompt=(
                        f"{item.image_prompt}. style {style_id} must be visible. "
                        f"template {template_id} must be structurally expressed."
                    ),
                )
            )
        images = [llm_image_ref(cleaned, "cleaned_reference")]
        user = (
            "Image 1 = CLEANED reference (this is what the image model will see).\n"
            + architect_user_prompt(context)
        )
        if original and original != cleaned:
            images.append(llm_image_ref(original, "original_dirty"))
            user = (
                "Image 1 = CLEANED reference (image model input). "
                "Image 2 = DIRTY/ORIGINAL (context only; do not reproduce UI).\n"
                + architect_user_prompt(context)
            )
        planned = PromptArchitectResult(
            reference_summary=result.reference_summary,
            identity_priority=result.identity_priority,
            art_direction=result.art_direction,
            candidates=tuple(tagged),
            llm_trace=LlmCallTrace(
                name="prompt_architect",
                model="stub",
                system=ARCHITECT_SYSTEM,
                user=user,
                images=tuple(images),
                output=json.dumps(
                    {
                        "reference_summary": result.reference_summary,
                        "candidates": [
                            {
                                "slot": item.slot,
                                "intention": item.intention,
                                "image_prompt": item.image_prompt,
                            }
                            for item in tagged
                        ],
                    }
                ),
            ),
        )
        return planned
