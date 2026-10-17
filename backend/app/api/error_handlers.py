"""Map every expected failure to the standard error envelope.

Unexpected exceptions are handled by ``UnhandledErrorsMiddleware`` instead of a bare
``Exception`` handler: Starlette runs that handler outside all user middleware, so its
500 responses would be missing CORS headers.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.error_responses import error_response
from app.core.constants import MISSING_FIELD_MESSAGES, ErrorCode
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
}
_HTTP_ERROR_MESSAGES = {
    404: "The requested resource was not found.",
    405: "This method is not allowed for this resource.",
    413: "The request body is too large.",
}
_DB_UNAVAILABLE_ERRORS = (OperationalError, InterfaceError, PoolTimeoutError)
_PYDANTIC_MESSAGE_PREFIX = "Value error, "


def _format_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    details = []
    for error in exc.errors():
        location, *path = error["loc"]
        field = ".".join(str(part) for part in path) or None
        message = str(error["msg"]).removeprefix(_PYDANTIC_MESSAGE_PREFIX)
        if error["type"] == "missing" and location == "body" and field is not None:
            message = MISSING_FIELD_MESSAGES.get(field, message)
        details.append({"location": location, "field": field, "message": message})
    return details


async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return error_response(
        exc.status_code, exc.code, exc.message, details=exc.details, headers=exc.headers
    )


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        422,
        ErrorCode.VALIDATION_ERROR,
        "The request is invalid.",
        details=_format_validation_errors(exc),
    )


async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_ERROR_CODES.get(exc.status_code, ErrorCode.HTTP_ERROR)
    message = _HTTP_ERROR_MESSAGES.get(exc.status_code, str(exc.detail))
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def handle_database_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    if isinstance(exc, _DB_UNAVAILABLE_ERRORS):
        logger.error("Database unavailable", exc_info=exc)
        return error_response(
            503,
            ErrorCode.SERVICE_UNAVAILABLE,
            "The service is temporarily unavailable. Please try again shortly.",
        )
    logger.error("Unexpected database error", exc_info=exc)
    return error_response(500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    # Starlette types handlers as taking a plain Exception; each handler below is only
    # ever called with the exception class it is registered for.
    handlers: dict[type[Exception], Callable[[Request, Any], Awaitable[JSONResponse]]] = {
        AppError: handle_app_error,
        RequestValidationError: handle_validation_error,
        StarletteHTTPException: handle_http_exception,
        SQLAlchemyError: handle_database_error,
    }
    for exc_class, handler in handlers.items():
        app.add_exception_handler(exc_class, handler)
