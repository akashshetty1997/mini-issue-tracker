from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.api.error_handlers import register_exception_handlers
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.constants import API_V1_PREFIX, APP_TITLE, APP_VERSION
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter
from app.db.session import create_db_engine, create_session_factory
from app.middleware import register_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory and composition root."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # Creating the engine doesn't connect; connections are opened lazily by the pool.
    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)
    app.state.rate_limiter = (
        RateLimiter.from_uri(settings.redis_url or "memory://")
        if settings.rate_limit_enabled
        else None
    )

    register_exception_handlers(app)
    register_middleware(app, settings)
    app.include_router(health.router)
    app.include_router(v1_router, prefix=API_V1_PREFIX)

    return app
