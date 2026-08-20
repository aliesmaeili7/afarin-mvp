from app.providers.vision.base import (
    CandidateQuality,
    InputQuality,
    PlannerContext,
    PlannerResult,
    QualityReport,
    RecipeProposal,
)

SMART_RECIPES = (
    RecipeProposal(
        style_id="photoreal_commercial",
        template_id="hero_product",
        title_fa="واقعی و واضح",
        description_fa="محصول در مرکز، نور استودیویی، مناسب فروش.",
        scene_direction="clean studio hero, soft key light",
        text_safe_area="bottom",
        identity_constraints=("keep major colors", "keep silhouette"),
    ),
    RecipeProposal(
        style_id="anime",
        template_id="illustrated_scene",
        title_fa="تصویرسازی زنده",
        description_fa="همان محصول در یک صحنه کشیده‌شده و رنگی.",
        scene_direction="illustrated campus or street scene around the product",
        text_safe_area="top",
        identity_constraints=("keep major colors", "keep graphic identity"),
    ),
    RecipeProposal(
        style_id="surreal",
        template_id="giant_miniature_world",
        title_fa="ایده غیرمنتظره",
        description_fa="محصول غول‌پیکر در یک دنیای کوچک.",
        scene_direction="giant product in a miniature city",
        text_safe_area="bottom",
        identity_constraints=("keep silhouette", "keep distinctive graphics"),
    ),
)


class StubVisualPlanner:
    name = "stub"
    model: str | None = None

    async def plan_recipes(
        self, image: bytes, context: PlannerContext
    ) -> PlannerResult:
        del image
        return PlannerResult(
            product_type="product",
            visual_identity=("visible product",),
            identity_constraints=("keep major colors", "keep silhouette"),
            unsuitable_style_ids=(),
            unsuitable_template_ids=(),
            input_quality=InputQuality("ok"),
            recommended_recipes=SMART_RECIPES,
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
