from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.constants import APP_TITLE, APP_VERSION
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory and composition root."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=APP_TITLE, version=APP_VERSION)
    app.state.settings = settings

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
