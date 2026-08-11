import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.errors import ApiError
from app.core.security import hash_anonymous_token, new_anonymous_token
from app.db.models import (
    AnonymousSession,
    Brand,
    Campaign,
    Product,
    ProductImage,
    Profile,
)
from app.services.storage.paths import SAMPLE_IMAGE_PATH


async def create_anonymous_session(
    session: AsyncSession,
) -> tuple[AnonymousSession, str]:
    """Mints a session and returns the raw token, which only ever goes into a cookie."""
    token = new_anonymous_token()
    row = AnonymousSession(token_hash=hash_anonymous_token(token))
    session.add(row)
    await session.flush()
    return row, token


async def get_or_create_profile(
    session: AsyncSession, user_id: uuid.UUID, email: str | None
) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is not None:
        return profile

    display_name = (email or "").split("@")[0] or "دوست عزیز"
    profile = Profile(
        user_id=user_id,
        display_name=display_name,
        email=email,
        locale="fa",
        free_campaigns_remaining=1,
    )
    session.add(profile)
    await session.flush()

    await seed_sample_campaign(session, profile)
    return profile


async def adopt_anonymous_session(
    session: AsyncSession,
    anonymous_session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    """
    Hands everything the anonymous visitor made to their new account (spec §11).

    Runs inside the request transaction with the session row locked, so two
    concurrent sign-ins cannot both claim it. No storage objects move: object
    keys are anchored on the campaign id, not on the owner.
    """
    anonymous = await session.scalar(
        select(AnonymousSession)
        .where(AnonymousSession.id == anonymous_session_id)
        .with_for_update()
    )
    if anonymous is None:
        return 0

    if anonymous.claimed_by_user_id is not None:
        if anonymous.claimed_by_user_id != user_id:
            raise ApiError("conflict", messages.ALREADY_CLAIMED)
        return 0

    campaigns = list(
        await session.scalars(
            select(Campaign).where(
                Campaign.anonymous_session_id == anonymous_session_id
            )
        )
    )

    product_ids = [c.product_id for c in campaigns if c.product_id]
    brand_ids = [c.brand_id for c in campaigns if c.brand_id]

    for campaign in campaigns:
        campaign.user_id = user_id
        campaign.anonymous_session_id = None

    if product_ids:
        await session.execute(
            update(Product)
            .where(Product.id.in_(product_ids), Product.user_id.is_(None))
            .values(user_id=user_id)
        )
    if brand_ids:
        await session.execute(
            update(Brand)
            .where(Brand.id.in_(brand_ids), Brand.user_id.is_(None))
            .values(user_id=user_id)
        )

    anonymous.claimed_by_user_id = user_id
    anonymous.claimed_at = datetime.now(UTC)

    await session.flush()
    return len(campaigns)


async def seed_sample_campaign(session: AsyncSession, profile: Profile) -> None:
    """
    One finished sample campaign so a brand-new account has something to look at
    on the dashboard, mirroring the seed the Phase 1 mock shipped. Explicitly
    labelled «نمونه» so it can never be mistaken for the seller's own work.
    """
    if profile.sample_seeded:
        return

    created_at = datetime.now(UTC) - timedelta(days=3)

    brand = Brand(
        user_id=profile.user_id,
        name="سحند",
        description="فروش زعفران و سوغات ایرانی با بسته‌بندی هدیه",
        category="مواد غذایی",
        instagram_handle="sahand.shop",
        target_audience="کسانی که دنبال هدیه لوکس ایرانی هستن",
        tone="لوکس و مؤدبانه",
        visual_style="luxury",
        primary_color="#7a2e1e",
        secondary_color="#e9b44c",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(brand)
    await session.flush()

    product = Product(
        user_id=profile.user_id,
        brand_id=brand.id,
        name="زعفران ممتاز (نمونه)",
        description="زعفران یک گرمی مناسب هدیه",
        price_text="۳۹۹ هزار تومان",
        main_benefit="بسته‌بندی هدیه و کیفیت صادراتی",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(product)
    await session.flush()

    session.add(
        ProductImage(
            product_id=product.id,
            storage_path=SAMPLE_IMAGE_PATH,
            is_primary=True,
            created_at=created_at,
        )
    )

    session.add(
        Campaign(
            user_id=profile.user_id,
            brand_id=brand.id,
            product_id=product.id,
            objective="sell_product",
            audience="کسانی که دنبال هدیه لوکس هستن",
            visual_style="luxury",
            status="ready",
            is_free_campaign=True,
            created_at=created_at,
            updated_at=created_at,
        )
    )

    profile.sample_seeded = True
    await session.flush()
