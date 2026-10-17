from collections.abc import Mapping
from typing import Any

from starlette.responses import JSONResponse

from app.core.constants import ErrorCode
from app.core.context import get_request_id
from app.schemas.common import ErrorBody, ErrorResponse


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    *,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a response in the standard error envelope.

    Used by exception handlers and by middleware, so every error has the same shape.
    """
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details, request_id=get_request_id())
    )
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )
