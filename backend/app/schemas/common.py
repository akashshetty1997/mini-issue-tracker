from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from app.core.constants import ErrorCode


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Shape of every error response the API returns."""

    error: ErrorBody


class Page[T](BaseModel):
    items: Sequence[T]
    total: int
    limit: int
    offset: int
