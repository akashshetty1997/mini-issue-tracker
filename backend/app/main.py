from fastapi import FastAPI

from app.api import health
from app.api.error_handlers import register_exception_handlers
from app.core.config import Settings, get_settings
from app.core.constants import APP_TITLE, APP_VERSION
from app.core.logging import configure_logging
from app.middleware import register_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory and composition root."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=APP_TITLE, version=APP_VERSION)
    app.state.settings = settings

    register_exception_handlers(app)
    register_middleware(app, settings)
    app.include_router(health.router)

    return app
