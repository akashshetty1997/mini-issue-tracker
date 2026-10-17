from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.constants import CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, CORS_EXPOSED_HEADERS
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.unhandled_errors import UnhandledErrorsMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Install middleware. Starlette wraps in reverse order of registration, so the
    resulting stack, outermost first, is: RequestId -> CORS -> UnhandledErrors -> app.

    CORS sits outside UnhandledErrors so that even 500 responses carry CORS headers and
    the browser can read the error envelope.
    """
    app.add_middleware(UnhandledErrorsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=CORS_EXPOSED_HEADERS,
    )
    app.add_middleware(RequestIdMiddleware)
