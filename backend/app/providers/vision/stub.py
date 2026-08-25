from __future__ import annotations

import json

from app.content.visual_catalog import compatibility
from app.providers.image.creative_prompts import INVENTED_TEXT_RULE
from app.providers.vision.base import (
    CLEAN_ANALYSIS,
    ArchitectCandidate,
    ArchitectColorAndMaterial,
    ArchitectComposition,
    ArchitectContext,
    ArchitectLighting,
    ArchitectOutput,
    ArchitectProduct,
    ArchitectScene,
    CampaignDirection,
    CandidateQuality,
    ExistingTextAndGraphics,
    IdentityFeature,
    InputQuality,
    LlmCallTrace,
    PlannerContext,
    PlannerResult,
    ProductPlacement,
    PromptArchitectResult,
    QualityReport,
    TypographySafeArea,
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
        directions = ALT_DIRECTIONS if context.previous_directions else SMART_DIRECTIONS
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
                        "product_visual_analysis": (
                            "visible product on a simple background"
                        ),
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


_STUB_SLOT_SPECS = (
    {
        "slot": 1,
        "intention": "safe",
        "camera": "three-quarter from the left, slightly above eye-level",
        "lens_feel": "35mm modest commercial",
        "position": "slightly off-center on the supporting surface",
        "environment": "windowed kitchen counter with morning bounce",
        "safe_position": "upper-left",
        "safe_description": "empty upper-left wall for later Persian overlay",
        "lighting_dir": "window key from camera-left",
        "intent": "clearest commercial still of this product",
    },
    {
        "slot": 2,
        "intention": "editorial",
        "camera": "low three-quarter, close to the contact surface",
        "lens_feel": "50mm editorial compression",
        "position": "asymmetric right-weighted placement",
        "environment": "marble bathroom niche with soft steam",
        "safe_position": "right",
        "safe_description": "clear right-edge band for Persian overlay",
        "lighting_dir": "overhead bounce with a warm side kick",
        "intent": "editorial composition, same product, still an ad",
    },
    {
        "slot": 3,
        "intention": "bold",
        "camera": "higher three-quarter with strong diagonal geometry",
        "lens_feel": "28mm environmental",
        "position": "dynamic low-left placement against depth",
        "environment": "sunlit terrazzo courtyard plinth",
        "safe_position": "sky",
        "safe_description": "empty sky band for Persian overlay",
        "lighting_dir": "hard sunlight from behind-right",
        "intent": "bold commercial reading of the same direction",
    },
)


def _stub_final_prompt(
    spec: dict, *, preserved: bool, style_id: str, template_id: str
) -> str:
    del template_id
    style_note = style_id.replace("_", " ")
    safe = spec["safe_description"]
    if preserved:
        return (
            f"{spec['camera']}, empty {spec['environment']}, no product drawn. "
            f"Leave a plausible empty contact region on the supporting surface. "
            f"{spec['lighting_dir']}, {style_note} materials in the set only. "
            f"{safe}. Do not invent readable text, logos, extra SKUs, "
            "or the product itself."
        )
    return (
        f"{spec['camera']} of this exact seller product, {spec['position']}, "
        f"in a {spec['environment']}. {spec['lighting_dir']}, {style_note} "
        f"atmosphere, product identity unchanged. {safe}. {INVENTED_TEXT_RULE}."
    )


def stub_architect_result(
    *, render_strategy: str = "reference_transform"
) -> PromptArchitectResult:
    preserved = render_strategy == "preserved_product_composite"
    identity = (
        IdentityFeature("silhouette", "critical"),
        IdentityFeature("major colors", "critical"),
    )
    candidates = []
    for spec in _STUB_SLOT_SPECS:
        prompt = _stub_final_prompt(
            spec,
            preserved=preserved,
            style_id="photoreal_commercial",
            template_id="hero_product",
        )
        candidates.append(
            _stub_candidate(
                spec,
                render_strategy=render_strategy,
                preserved=preserved,
                identity=identity,
                prompt=prompt,
                surface="table",
            )
        )
    return PromptArchitectResult(
        reference_summary="visible seller product on a clean crop",
        candidates=tuple(candidates),
    )


def _stub_candidate(
    spec: dict,
    *,
    render_strategy: str,
    preserved: bool,
    identity: tuple[IdentityFeature, ...],
    prompt: str,
    surface: str,
) -> ArchitectCandidate:
    return ArchitectCandidate(
        slot=int(spec["slot"]),
        intention=str(spec["intention"]),
        creative_intent=str(spec["intent"]),
        product=ArchitectProduct(
            role_in_scene=(
                "absent; empty contact region awaits a real cutout"
                if preserved
                else "the single advertised SKU, fully visible"
            ),
            identity_priority=identity,
            existing_text_and_graphics=ExistingTextAndGraphics(
                preserve=True,
                instructions="keep graphics already on the product",
            ),
        ),
        scene=ArchitectScene(
            environment=str(spec["environment"]),
            story_or_context="quiet commercial still",
            foreground="simple supporting surface",
            background="designed environment, no UI",
            props=("one category-relevant prop",),
        ),
        composition=ArchitectComposition(
            camera=str(spec["camera"]),
            lens_feel=str(spec["lens_feel"]),
            product_scale="product occupies about 55 percent of the frame",
            product_position=str(spec["position"]),
            human_or_pose="",
            depth="clear foreground midground background",
        ),
        lighting=ArchitectLighting(
            direction=str(spec["lighting_dir"]),
            quality="controlled commercial",
            mood="clear and sellable",
        ),
        color_and_material=ArchitectColorAndMaterial(
            palette="product-true colors",
            material_treatment="keep real product materials",
        ),
        typography_safe_area=TypographySafeArea(
            position=str(spec["safe_position"]),
            description=str(spec["safe_description"]),
        ),
        must_preserve=("silhouette", "major colors"),
        must_not_generate=("readable invented text", "Instagram UI"),
        render_strategy=render_strategy,
        final_prompt=prompt,
        has_product_placement=preserved,
        product_placement=ProductPlacement(
            x=0.5,
            y=0.58,
            width=0.42,
            rotation_degrees=0.0,
            contact_surface=surface if preserved else "",
            shadow_direction="down",
            shadow_softness="soft",
        )
        if preserved
        else ProductPlacement(x=0.0, y=0.0, width=0.0, rotation_degrees=0.0),
        output=ArchitectOutput(
            aspect_ratio="4:5", format="instagram advertisement still"
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
        correction: str | None = None,
    ) -> PromptArchitectResult:
        style_id = str(context.recipe.get("style_id") or "photoreal_commercial")
        template_id = str(context.recipe.get("template_id") or "hero_product")
        preserved = context.render_strategy == "preserved_product_composite"
        surface = "table"
        if str(context.recipe.get("template_id")) == "product_pedestal":
            surface = "plinth"
        if str(context.recipe.get("template_id")) == "floating_product":
            surface = "none"
        if str(context.recipe.get("template_id")) == "flat_lay":
            surface = "linen"
        identity = (
            IdentityFeature("silhouette", "critical"),
            IdentityFeature("major colors", "critical"),
        )
        tagged = []
        for spec in _STUB_SLOT_SPECS:
            prompt = _stub_final_prompt(
                spec, preserved=preserved, style_id=style_id, template_id=template_id
            )
            tagged.append(
                _stub_candidate(
                    spec,
                    render_strategy=context.render_strategy,
                    preserved=preserved,
                    identity=identity,
                    prompt=prompt,
                    surface=surface,
                )
            )
        images = [llm_image_ref(cleaned, "cleaned_reference")]
        user = (
            "Image 1 = CLEANED reference (this is what the image model will see).\n"
            + architect_user_prompt(context, correction=correction)
        )
        if original and original != cleaned:
            images.append(llm_image_ref(original, "original_dirty"))
            user = (
                "Image 1 = CLEANED reference (image model input). "
                "Image 2 = DIRTY/ORIGINAL (context only; do not reproduce UI).\n"
                + architect_user_prompt(context, correction=correction)
            )
        return PromptArchitectResult(
            reference_summary="visible seller product on a clean crop",
            candidates=tuple(tagged),
            llm_trace=LlmCallTrace(
                name="prompt_architect",
                model="stub",
                system=ARCHITECT_SYSTEM,
                user=user,
                images=tuple(images),
                output=json.dumps(
                    {
                        "reference_summary": "visible seller product on a clean crop",
                        "candidates": [
                            {
                                "slot": item.slot,
                                "intention": item.intention,
                                "final_prompt": item.final_prompt,
                            }
                            for item in tagged
                        ],
                    }
                ),
            ),
        )
