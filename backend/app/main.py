import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    assets,
    brands,
    campaigns,
    catalog,
    chat,
    education,
    generation,
    session,
)
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import dispose_engine
from app.services.campaigns.cutout import rembg_available
from app.services.storage import get_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.supabase_service_role_key:
        # Both buckets are private. Creating them at boot keeps a fresh
        # environment from failing on the seller's first upload.
        storage = get_storage()
        for bucket in (settings.bucket_product_images, settings.bucket_brand_assets):
            try:
                await storage.ensure_bucket(bucket)
            except Exception as error:
                logger.warning("could not ensure bucket %s: %s", bucket, error)
    else:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not set; uploads will fail")

    if rembg_available():
        logger.info("product cutout is active (rembg)")
    else:
        logger.warning(
            "rembg is not installed; campaigns will composite the seller's "
            "approved crop instead of a transparent cutout. "
            "Install with: uv sync --extra cutout"
        )

    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Afarin API", version="0.2.0", lifespan=lifespan)

    # An exact origin allowlist, not a wildcard: the anonymous session cookie
    # rides on these requests, and credentialed CORS forbids `*`.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["authorization", "content-type"],
    )

    register_error_handlers(app)

    app.include_router(session.router)
    app.include_router(campaigns.router)
    app.include_router(generation.router)
    app.include_router(brands.router)
    app.include_router(assets.router)
    app.include_router(catalog.router)
    app.include_router(education.router)
    app.include_router(chat.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
