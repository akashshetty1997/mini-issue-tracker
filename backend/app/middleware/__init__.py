from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.constants import CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, CORS_EXPOSED_HEADERS
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.body_size_limit import BodySizeLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.unhandled_errors import UnhandledErrorsMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Install middleware. Starlette wraps in reverse order of registration, so the
    resulting stack, outermost first, is:

        RequestId -> AccessLog -> SecurityHeaders -> CORS -> UnhandledErrors
            -> BodySizeLimit -> app

    - RequestId is outermost so every log line and response, errors included, has an id.
    - AccessLog sees the final status of every response, including generated 500s.
    - CORS sits outside UnhandledErrors and BodySizeLimit so their 500/413 responses still
      carry CORS headers and the browser can read the error envelope.
    """
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(UnhandledErrorsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=CORS_EXPOSED_HEADERS,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
