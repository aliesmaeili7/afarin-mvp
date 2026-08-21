from app.providers.vision.base import (
    CampaignDirection,
    CandidateQuality,
    InputQuality,
    PlannerContext,
    PlannerResult,
    QualityReport,
)

SMART_DIRECTIONS = (
    CampaignDirection(
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
    CampaignDirection(
        title_fa="تصویرسازی زنده",
        description_fa="همان محصول در یک صحنه کشیده‌شده و رنگی.",
        angle="illustrated lifestyle",
        headline_fa="یه حال و هوای تازه",
        visual_direction="تصویرسازی رنگی اطراف محصول",
        style_id="anime",
        template_id="illustrated_scene",
        identity_constraints=("keep major colors", "keep graphic identity"),
        image_direction="illustrated campus or street scene around the product",
        background_prompt="illustrated color wash environment, no product, no text",
        text_safe_area="top",
    ),
    CampaignDirection(
        title_fa="ایده غیرمنتظره",
        description_fa="محصول غول‌پیکر در یک دنیای کوچک.",
        angle="surreal scale",
        headline_fa="بزرگ‌تر از چیزی که فکر می‌کنی",
        visual_direction="مقیاس سوررئال، محصول غول‌پیکر",
        style_id="surreal",
        template_id="giant_miniature_world",
        identity_constraints=("keep silhouette", "keep distinctive graphics"),
        image_direction="giant product in a miniature city",
        background_prompt="miniature city environment, dusk light, no product, no text",
        text_safe_area="bottom",
    ),
)

ALT_DIRECTIONS = (
    CampaignDirection(
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
    CampaignDirection(
        title_fa="آبرنگ آرام",
        description_fa="نقاشی ملایم با فضای خالی برای متن.",
        angle="watercolor story",
        headline_fa="نرم، ساده، ماندگار",
        visual_direction="بافت آبرنگ و کاغذ مرطوب",
        style_id="watercolor_illustration",
        template_id="flat_lay",
        identity_constraints=("keep major colors",),
        image_direction="watercolor flat lay of the product on paper texture",
        background_prompt="wet paper watercolor wash, empty, no text",
        text_safe_area="bottom",
    ),
    CampaignDirection(
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
        self, image: bytes, context: PlannerContext
    ) -> PlannerResult:
        del image
        directions = (
            ALT_DIRECTIONS if context.previous_directions else SMART_DIRECTIONS
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
        del reference, context
        rows = tuple(
            CandidateQuality(slot=index + 1, hard_failed=False)
            for index in range(len(candidates))
        )
        return QualityReport(candidates=rows)
