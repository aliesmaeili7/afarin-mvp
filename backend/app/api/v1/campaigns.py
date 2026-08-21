import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Request, Response, UploadFile
from sqlalchemy import func, select

from app.api.v1.session import ensure_anonymous_owner
from app.core import messages
from app.core.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.enums import (
    ASSET_REWRITE_INTENTS,
    COPY_REWRITE_INTENTS,
    STORY_SCENE_TYPES,
    VISUAL_FINAL_TYPES,
)
from app.core.errors import ApiError, conflict, generation_failed, invalid, not_found
from app.db.models import (
    Brand,
    Campaign,
    CampaignAsset,
    CampaignCopy,
    CampaignVisualAttempt,
    CampaignVisualCandidate,
    GenerationJob,
    Product,
    ProductImage,
)
from app.providers.image import get_image_provider
from app.providers.llm import get_content_provider
from app.schemas.domain import (
    CampaignAssetOut,
    CampaignConceptOut,
    CampaignCopyOut,
    CampaignDetailOut,
    CampaignOut,
    CampaignStatusOut,
    CampaignSummaryOut,
    ProductImageOut,
    ProductOut,
    VisualAttemptOut,
    VisualCandidateOut,
)
from app.schemas.requests import (
    AssetTextIn,
    CreateCampaignIn,
    CropIn,
    ProductIn,
    RewriteIn,
    UpdateCampaignIn,
    UpdateCopyIn,
    VisualRecipeIn,
)
from app.services.campaigns import cost as budgets
from app.services.campaigns import creative as creative_visuals
from app.services.campaigns import jobs as job_records
from app.services.campaigns import materialize as materializer
from app.services.campaigns import planner as visual_planner
from app.services.campaigns import queries, summaries
from app.services.campaigns import recipes as recipe_builder
from app.services.campaigns import visuals as visualizer
from app.services.campaigns import text_layers as type_layers
from app.services.campaigns.crop import parse_crop
from app.services.campaigns.ownership import get_owned_campaign
from app.services.campaigns.product_media import assign_suggested_crop, save_crop
from app.services.storage import (
    StorageRef,
    get_storage,
    parse,
    product_image_key,
    validate_upload,
)
from app.services.storage.paths import SAMPLE_IMAGE_PATH

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignOut)
async def create_campaign(
    body: CreateCampaignIn,
    request: Request,
    response: Response,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
) -> Campaign:
    owner = await ensure_anonymous_owner(
        request, response, session, principal, settings
    )

    campaign = Campaign(
        user_id=owner.user_id,
        anonymous_session_id=owner.anonymous_session_id,
        brand_id=body.brand_id,
        status="draft",
        is_free_campaign=True,
    )
    session.add(campaign)
    await session.flush()
    return campaign


@router.get("", response_model=list[CampaignSummaryOut])
async def list_campaigns(
    session: SessionDep, principal: PrincipalDep
) -> list[CampaignSummaryOut]:
    if principal.is_authenticated:
        condition = Campaign.user_id == principal.user_id
    elif principal.anonymous_session_id is not None:
        condition = Campaign.anonymous_session_id == principal.anonymous_session_id
    else:
        return []

    campaigns = list(
        await session.scalars(
            select(Campaign).where(condition).order_by(Campaign.created_at.desc())
        )
    )

    result: list[CampaignSummaryOut] = []
    for campaign in campaigns:
        # Listing is a read. The seeded sample has no generated ads yet; the
        # card falls back to its product photo. Materializing here would fire
        # the live LLM for every new account's dashboard visit.
        result.append(await summaries.summarize(session, campaign))
    return result


@router.get("/{campaign_id}", response_model=CampaignDetailOut)
async def get_campaign(
    campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> CampaignDetailOut:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    await summaries.ensure_materialized(session, campaign)

    return CampaignDetailOut(
        campaign=CampaignOut.model_validate(campaign),
        product=await queries.product_of(session, campaign),
        product_images=await queries.images_of(session, campaign),
        concepts=await queries.concepts_of(session, campaign.id),
        copies=await queries.copies_of(session, campaign.id),
        assets=await queries.assets_of(session, campaign.id),
        brand=await queries.brand_of(session, campaign),
        visual_attempt=await _visual_attempt_out(session, campaign),
        visual_candidates=await _visual_candidates_out(session, campaign),
    )


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: UpdateCampaignIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> Campaign:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    provided = body.model_fields_set
    changed = False

    if "objective" in provided:
        changed = changed or materializer.blank_text(
            body.objective
        ) != materializer.blank_text(campaign.objective)
        campaign.objective = body.objective
    if "audience" in provided:
        changed = changed or materializer.blank_text(
            body.audience
        ) != materializer.blank_text(campaign.audience)
        campaign.audience = body.audience
    if "visual_style" in provided:
        changed = changed or materializer.blank_text(
            body.visual_style
        ) != materializer.blank_text(campaign.visual_style)
        campaign.visual_style = body.visual_style
    if "visual_creation_mode" in provided:
        mode = body.visual_creation_mode
        if mode is not None and mode not in ("accurate", "creative"):
            raise invalid(messages.VISUAL_MODE_REQUIRED)
        campaign.visual_creation_mode = mode
    if "brand_id" in provided:
        changed = changed or body.brand_id != campaign.brand_id
        campaign.brand_id = body.brand_id

    await materializer.invalidate_concepts_if_stale(session, campaign, changed)

    if (
        campaign.status == "draft"
        and campaign.product_id
        and campaign.objective
        and campaign.visual_style
    ):
        campaign.status = "brief_complete"

    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return campaign


@router.post("/{campaign_id}/product", response_model=ProductOut)
async def save_product(
    campaign_id: uuid.UUID,
    body: ProductIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> Product:
    if not body.name or not body.name.strip():
        raise invalid(messages.PRODUCT_NAME_REQUIRED)

    campaign = await get_owned_campaign(session, principal, campaign_id)
    product = await _ensure_product(session, campaign)
    brand = await queries.brand_of(session, campaign)

    incoming_name = body.name.strip()
    incoming_description = materializer.blank_text(body.description)
    incoming_price = materializer.blank_text(body.price_text)
    incoming_benefit = materializer.blank_text(body.main_benefit)
    incoming_brand = materializer.blank_text(body.brand_name)

    changed = (
        incoming_name != (product.name or "")
        or incoming_description != materializer.blank_text(product.description)
        or incoming_price != materializer.blank_text(product.price_text)
        or incoming_benefit != materializer.blank_text(product.main_benefit)
    )
    if incoming_brand is not None:
        changed = changed or incoming_brand != (brand.name if brand else None)

    product.name = incoming_name
    product.description = incoming_description
    product.price_text = incoming_price
    product.main_benefit = incoming_benefit
    product.updated_at = datetime.now(UTC)

    brand_name = incoming_brand
    if brand_name:
        await _attach_brand(session, campaign, product, brand_name, principal.user_id)

    await materializer.invalidate_concepts_if_stale(session, campaign, changed)

    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return product


@router.post("/{campaign_id}/images", response_model=list[ProductImageOut])
async def upload_product_images(
    campaign_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    settings: SettingsDep,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> list[ProductImage]:
    if not files:
        return []

    campaign = await get_owned_campaign(session, principal, campaign_id)
    product = await _ensure_product(session, campaign)

    existing = await queries.images_of(session, campaign)
    if len(existing) + len(files) > settings.max_product_images:
        raise invalid(messages.TOO_MANY_IMAGES)

    storage = get_storage()
    created: list[ProductImage] = []

    for index, upload in enumerate(files):
        content = await upload.read()
        extension = validate_upload(
            content, upload.content_type or "", settings.max_upload_bytes
        )

        image = ProductImage(
            product_id=product.id,
            storage_path="",
            is_primary=not existing and index == 0,
        )
        session.add(image)
        await session.flush()

        # Keyed by campaign, not owner, so adoption never has to move bytes.
        ref = StorageRef(
            bucket=settings.bucket_product_images,
            key=product_image_key(campaign.id, image.id, extension),
        )
        await storage.upload(ref, content, upload.content_type or "image/webp")
        image.storage_path = ref.to_path()
        await assign_suggested_crop(session, campaign, image, content)
        created.append(image)

    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return created


@router.patch("/{campaign_id}/images/{image_id}/crop", response_model=ProductImageOut)
async def update_product_crop(
    campaign_id: uuid.UUID,
    image_id: uuid.UUID,
    body: CropIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> ProductImage:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    image = await session.scalar(
        select(ProductImage).where(ProductImage.id == image_id)
    )
    if image is None or (
        campaign.product_id is not None and image.product_id != campaign.product_id
    ):
        raise not_found(messages.IMAGE_NOT_FOUND)
    try:
        rect = parse_crop(body.model_dump())
    except ValueError as error:
        raise invalid(messages.CROP_INVALID) from error
    await save_crop(session, campaign, image, rect)
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return image


@router.delete("/{campaign_id}/images/{image_id}", status_code=204)
async def delete_product_image(
    campaign_id: uuid.UUID,
    image_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> None:
    campaign = await get_owned_campaign(session, principal, campaign_id)

    image = await session.scalar(
        select(ProductImage).where(ProductImage.id == image_id)
    )
    if image is None or (
        campaign.product_id is not None and image.product_id != campaign.product_id
    ):
        raise not_found(messages.IMAGE_NOT_FOUND)

    storage_path = image.storage_path
    crop_path = image.crop_storage_path
    was_primary = image.is_primary
    await session.delete(image)
    await session.flush()

    if was_primary:
        remaining = await queries.images_of(session, campaign)
        if remaining:
            remaining[0].is_primary = True

    storage = get_storage()
    for path in (storage_path, crop_path):
        ref = parse(path) if path else None
        if ref is not None:
            await storage.remove(ref)

    await session.flush()


@router.post("/{campaign_id}/images/sample", response_model=list[ProductImageOut])
async def use_sample_product(
    campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[ProductImage]:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    product = await _ensure_product(session, campaign)

    for image in await queries.images_of(session, campaign):
        storage = get_storage()
        for path in (image.storage_path, image.crop_storage_path):
            ref = parse(path) if path else None
            if ref is not None:
                await storage.remove(ref)
        await session.delete(image)
    await session.flush()

    image = ProductImage(
        product_id=product.id, storage_path=SAMPLE_IMAGE_PATH, is_primary=True
    )
    session.add(image)
    await session.flush()
    await assign_suggested_crop(session, campaign, image, b"")

    # Prefill the brief so the demo path shows a complete example.
    product.name = product.name or "زعفران ممتاز"
    product.description = product.description or "زعفران یک گرمی مناسب هدیه"
    product.price_text = product.price_text or "۳۹۹ هزار تومان"
    product.main_benefit = product.main_benefit or "بسته‌بندی هدیه و کیفیت صادراتی"
    product.updated_at = datetime.now(UTC)

    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return [image]


@router.post(
    "/{campaign_id}/concepts/generate", response_model=list[CampaignConceptOut]
)
async def generate_concepts(
    campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
):
    campaign = await get_owned_campaign(session, principal, campaign_id)

    if not campaign.objective or not campaign.visual_style:
        raise invalid(messages.BRIEF_INCOMPLETE)

    campaign.concept_round = (
        0 if campaign.concept_round is None else campaign.concept_round + 1
    )

    try:
        result = await visual_planner.plan_directions(
            session, campaign, principal.user_id
        )
    except Exception as error:
        campaign.concept_round = (
            None if campaign.concept_round == 0 else campaign.concept_round - 1
        )
        await session.commit()
        if isinstance(error, ApiError):
            raise
        raise generation_failed() from error

    if not result.input_quality.ok:
        campaign.concept_round = (
            None if campaign.concept_round == 0 else campaign.concept_round - 1
        )
        await session.flush()
        raise invalid(messages.INPUT_QUALITY_NEEDS_FIX)

    created = await visual_planner.write_directions(session, campaign, result)

    campaign.selected_concept_id = None
    campaign.status = "concepts_ready"
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return created


@router.post("/{campaign_id}/concepts/{concept_id}/select", response_model=CampaignOut)
async def select_concept(
    campaign_id: uuid.UUID,
    concept_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> Campaign:
    campaign = await get_owned_campaign(session, principal, campaign_id)

    concepts = await queries.concepts_of(session, campaign.id)
    if not any(concept.id == concept_id for concept in concepts):
        raise not_found(messages.CONCEPT_NOT_FOUND)

    chosen = None
    for concept in concepts:
        concept.selected = concept.id == concept_id
        if concept.selected:
            chosen = concept

    campaign.selected_concept_id = concept_id
    campaign.status = "concept_selected"
    if chosen is not None:
        recipe = visual_planner.recipe_for_concept(
            chosen, planner=campaign.planner_result_json or {}
        )
        if recipe is not None:
            campaign.visual_recipe_json = recipe
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return campaign


@router.post("/{campaign_id}/visual/recipe", response_model=CampaignOut)
async def save_visual_recipe(
    campaign_id: uuid.UUID,
    body: VisualRecipeIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> Campaign:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    existing = campaign.visual_recipe_json or {}
    recommended = recipe_builder.recommended_from(existing)
    if body.source == "smart" and not recommended:
        recommended = {"style_id": body.style_id, "template_id": body.template_id}
    campaign.visual_recipe_json = recipe_builder.recipe_from_ids(
        body.style_id,
        body.template_id,
        source=body.source if body.source in ("smart", "custom") else "custom",
        scene_direction=body.scene_direction or str(existing.get("scene_direction") or ""),
        identity_constraints=(
            body.identity_constraints
            if body.identity_constraints is not None
            else list(existing.get("identity_constraints") or [])
        ),
        title_fa=body.title_fa or existing.get("title_fa"),
        description_fa=body.description_fa or existing.get("description_fa"),
        warning_fa=body.warning_fa or str(existing.get("warning_fa") or ""),
        text_safe_area=body.text_safe_area or existing.get("text_safe_area"),
        planner=existing.get("planner") if isinstance(existing.get("planner"), dict) else {},
        recommended=recommended or {
            "style_id": body.style_id,
            "template_id": body.template_id,
        },
    )
    if campaign.visual_creation_mode != "creative":
        campaign.visual_creation_mode = "creative"
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return campaign


@router.post(
    "/{campaign_id}/visual/candidates/{candidate_id}/select",
    response_model=CampaignOut,
)
async def select_visual_candidate(
    campaign_id: uuid.UUID,
    candidate_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> Campaign:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    user_id = principal.require_user()
    await creative_visuals.select_winner(session, campaign, candidate_id, user_id)
    await session.flush()
    return campaign


@router.post("/{campaign_id}/visual/regenerate", response_model=CampaignStatusOut)
async def regenerate_visual_candidates(
    campaign_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignStatusOut:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    user_id = principal.require_user()
    if (campaign.visual_creation_mode or "accurate") != "creative":
        raise invalid(messages.VISUAL_RECIPE_REQUIRED)
    recipe = campaign.visual_recipe_json or {}
    if not recipe.get("style_id"):
        raise invalid(messages.VISUAL_RECIPE_REQUIRED)
    if campaign.status not in ("candidates_ready", "ready", "partial_failed"):
        raise invalid(messages.CANDIDATE_REQUIRED)
    await budgets.assert_can_start_attempt(session, campaign)

    active = await session.scalar(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign.id,
            GenerationJob.job_type.in_(("campaign_generation", "image_generation")),
            GenerationJob.status.in_(("queued", "processing")),
        )
    )
    if active is not None:
        raise conflict(messages.GENERATION_BUSY)

    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=user_id,
        job_type="image_generation",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={},
    )
    session.add(job)
    campaign.status = "generating"
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    from app.api.v1 import generation as generation_api

    return await generation_api._run_images(session, campaign, job)


async def _visual_attempt_out(
    session, campaign: Campaign
) -> VisualAttemptOut | None:
    if campaign.current_visual_attempt_id is None:
        return None
    row = await session.scalar(
        select(CampaignVisualAttempt).where(
            CampaignVisualAttempt.id == campaign.current_visual_attempt_id
        )
    )
    if row is None:
        return None
    return VisualAttemptOut.model_validate(row)


async def _visual_candidates_out(
    session, campaign: Campaign
) -> list[VisualCandidateOut]:
    if campaign.current_visual_attempt_id is None:
        return []
    rows = await session.scalars(
        select(CampaignVisualCandidate)
        .where(
            CampaignVisualCandidate.attempt_id == campaign.current_visual_attempt_id
        )
        .order_by(CampaignVisualCandidate.slot, CampaignVisualCandidate.created_at)
    )
    return [VisualCandidateOut.model_validate(row) for row in rows]


@router.patch("/{campaign_id}/copy/{copy_id}", response_model=CampaignCopyOut)
async def update_copy(
    campaign_id: uuid.UUID,
    copy_id: uuid.UUID,
    body: UpdateCopyIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignCopy:
    campaign = await get_owned_campaign(session, principal, campaign_id)

    copy = await session.scalar(
        select(CampaignCopy).where(
            CampaignCopy.id == copy_id, CampaignCopy.campaign_id == campaign.id
        )
    )
    if copy is None:
        raise not_found(messages.COPY_NOT_FOUND)

    copy.content = body.content
    copy.updated_at = datetime.now(UTC)
    await session.flush()
    return copy


@router.post("/{campaign_id}/copy/{copy_id}/rewrite", response_model=CampaignCopyOut)
async def rewrite_copy(
    campaign_id: uuid.UUID,
    copy_id: uuid.UUID,
    body: RewriteIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignCopy:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    copy = await session.scalar(
        select(CampaignCopy).where(
            CampaignCopy.id == copy_id, CampaignCopy.campaign_id == campaign.id
        )
    )
    if copy is None:
        raise not_found(messages.COPY_NOT_FOUND)
    if body.intent not in COPY_REWRITE_INTENTS:
        raise invalid(messages.REWRITE_NOT_ALLOWED)

    ctx = await queries.build_copy_context(session, campaign)
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=principal.user_id,
        job_type="copy_rewrite",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "intent": body.intent,
            "copy_type": copy.copy_type,
            "copy_id": str(copy.id),
        },
    )
    session.add(job)
    await session.flush()

    try:
        rewritten = await get_content_provider().rewrite_text(
            ctx,
            intent=body.intent,
            current=copy.content,
            field=copy.copy_type,
        )
    except Exception as error:
        job_records.mark_failed(job, error)
        await session.commit()
        if isinstance(error, ApiError):
            raise
        raise generation_failed() from error

    copy.content = rewritten
    copy.updated_at = datetime.now(UTC)
    if body.intent == "stronger_cta" and copy.copy_type == "cta":
        await _sync_asset_cta(session, campaign.id, rewritten)
    job_records.mark_succeeded(job, {"text_fa": rewritten})
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return copy


@router.post(
    "/{campaign_id}/assets/{asset_id}/rewrite",
    response_model=CampaignAssetOut,
)
async def rewrite_asset(
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    body: RewriteIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignAsset:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    asset = await _owned_asset(session, campaign.id, asset_id)
    if body.intent not in ASSET_REWRITE_INTENTS:
        raise invalid(messages.REWRITE_NOT_ALLOWED)

    spec = dict(asset.metadata_json or {})
    field = "headline" if body.intent == "new_headline" else "cta"
    current = (
        spec.get("headline_fa") if field == "headline" else spec.get("cta_fa")
    ) or ""

    ctx = await queries.build_copy_context(session, campaign)
    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=principal.user_id,
        job_type="copy_rewrite",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "intent": body.intent,
            "asset_id": str(asset.id),
            "field": field,
        },
    )
    session.add(job)
    await session.flush()

    try:
        rewritten = await get_content_provider().rewrite_text(
            ctx, intent=body.intent, current=current, field=field
        )
    except Exception as error:
        job_records.mark_failed(job, error)
        await session.commit()
        if isinstance(error, ApiError):
            raise
        raise generation_failed() from error

    if field == "headline":
        spec["headline_fa"] = rewritten
        spec = type_layers.apply_role_text(spec, "headline", rewritten)
    else:
        spec["cta_fa"] = rewritten
        spec = type_layers.apply_role_text(spec, "cta", rewritten)
        await _sync_cta_copy(session, campaign.id, rewritten)
    asset.metadata_json = spec
    job_records.mark_succeeded(job, {"text_fa": rewritten})
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return asset


@router.post(
    "/{campaign_id}/assets/{asset_id}/regenerate",
    response_model=CampaignAssetOut,
)
async def regenerate_asset(
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignAsset:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    if (campaign.visual_creation_mode or "accurate") == "creative":
        raise invalid(messages.ACCURATE_REGEN_ONLY)
    asset = await _owned_asset(session, campaign.id, asset_id)

    active = await session.scalar(
        select(GenerationJob).where(
            GenerationJob.campaign_id == campaign.id,
            GenerationJob.job_type.in_(("campaign_generation", "image_generation")),
            GenerationJob.status.in_(("queued", "processing")),
        )
    )
    if active is not None:
        raise conflict(messages.GENERATION_BUSY)

    aspect = (
        visualizer.ASPECT_9X16
        if asset.asset_type in STORY_SCENE_TYPES
        else visualizer.ASPECT_4X5
    )
    previous = await session.scalar(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.campaign_id == campaign.id,
            GenerationJob.job_type == "image_generation",
        )
    )
    variation = int(previous or 0) + 1

    job = GenerationJob(
        campaign_id=campaign.id,
        user_id=principal.user_id,
        job_type="image_generation",
        status="processing",
        started_at=datetime.now(UTC),
        input_json={
            "aspect": aspect,
            "asset_type": asset.asset_type,
            "variation": variation,
        },
    )
    session.add(job)
    await session.flush()

    provider_name = get_image_provider().name
    try:
        usage = await visualizer.regenerate_scene(
            session, campaign, aspect=aspect, variation=variation
        )
    except Exception as error:
        job_records.mark_image_failed(job, error, provider=provider_name)
        await session.commit()
        if isinstance(error, ApiError):
            raise
        raise generation_failed() from error

    if usage is None:
        job_records.mark_image_failed(
            job,
            RuntimeError("scene generation returned nothing"),
            provider=provider_name,
        )
        await session.commit()
        raise generation_failed()

    job_records.mark_image_succeeded(
        job, usage, provider=provider_name, output={"aspect": aspect}
    )
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    await session.refresh(asset)
    return asset


@router.patch("/{campaign_id}/assets/{asset_id}", response_model=CampaignAssetOut)
async def update_asset_text(
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    body: AssetTextIn,
    session: SessionDep,
    principal: PrincipalDep,
) -> CampaignAsset:
    campaign = await get_owned_campaign(session, principal, campaign_id)
    asset = await _owned_asset(session, campaign.id, asset_id)

    spec = dict(asset.metadata_json or {})
    patch = body.model_dump(exclude_unset=True)
    layers_touched = "text_layers" in body.model_fields_set
    layers_value = patch.pop("text_layers", None) if layers_touched else None

    role_for_field = {
        "headline_fa": "headline",
        "subheadline_fa": "subheadline",
        "cta_fa": "cta",
        "price_text": "price",
    }
    for key, value in patch.items():
        spec[key] = value
        role = role_for_field.get(key)
        if role is not None:
            spec = type_layers.apply_role_text(spec, role, value or "")

    if layers_touched:
        spec = type_layers.apply_text_layers(spec, layers_value)

    asset.metadata_json = spec
    campaign.updated_at = datetime.now(UTC)
    await session.flush()
    return asset


async def _sync_asset_cta(session, campaign_id: uuid.UUID, cta_fa: str) -> None:
    assets = await queries.assets_of(session, campaign_id)
    for asset in assets:
        if asset.asset_type not in VISUAL_FINAL_TYPES:
            continue
        spec = dict(asset.metadata_json or {})
        spec["cta_fa"] = cta_fa
        spec = type_layers.apply_role_text(spec, "cta", cta_fa)
        asset.metadata_json = spec


async def _sync_cta_copy(session, campaign_id: uuid.UUID, cta_fa: str) -> None:
    copy = await session.scalar(
        select(CampaignCopy).where(
            CampaignCopy.campaign_id == campaign_id, CampaignCopy.copy_type == "cta"
        )
    )
    if copy is not None:
        copy.content = cta_fa
        copy.updated_at = datetime.now(UTC)


async def _owned_asset(session, campaign_id: uuid.UUID, asset_id: uuid.UUID):
    asset = await session.scalar(
        select(CampaignAsset).where(
            CampaignAsset.id == asset_id, CampaignAsset.campaign_id == campaign_id
        )
    )
    if asset is None:
        raise not_found(messages.ASSET_NOT_FOUND)
    return asset


async def _ensure_product(session, campaign: Campaign) -> Product:
    product = await queries.product_of(session, campaign)
    if product is not None:
        return product

    product = Product(user_id=campaign.user_id, brand_id=campaign.brand_id, name="")
    session.add(product)
    await session.flush()
    campaign.product_id = product.id
    return product


async def _attach_brand(
    session, campaign: Campaign, product: Product, brand_name: str, user_id
) -> None:
    """Reuses a brand of the same name so the Brand Kit gathers no duplicates."""
    existing = await session.scalar(
        select(Brand).where(
            Brand.name == brand_name,
            (Brand.user_id == user_id) | (Brand.id == campaign.brand_id),
        )
    )
    if existing is None:
        existing = Brand(
            user_id=user_id, name=brand_name, visual_style=campaign.visual_style
        )
        session.add(existing)
        await session.flush()

    campaign.brand_id = existing.id
    product.brand_id = existing.id
