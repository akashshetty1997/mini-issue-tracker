"""Infrastructure probes. Unversioned: they describe the process, not the API contract."""

import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep
from app.core.rate_limit import RateLimiter
from app.schemas.meta import HealthRead, ReadinessRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> HealthRead:
    return HealthRead(status="ok")


@router.get("/ready", summary="Readiness probe")
def ready(session: SessionDep, request: Request, response: Response) -> ReadinessRead:
    """Only the database decides readiness. The rate-limit store is reported but can't
    make the instance unready: without it the limiter degrades to in-memory counters, and
    taking healthy instances out of rotation over it would cause an outage."""
    checks = {"database": "ok"}
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness check failed: database unavailable", exc_info=True)
        checks["database"] = "unavailable"

    limiter: RateLimiter | None = request.app.state.rate_limiter
    if limiter is not None:
        checks["rate_limit_storage"] = "ok" if limiter.storage_healthy() else "degraded"

    if checks["database"] != "ok":
        response.status_code = 503
        return ReadinessRead(status="unavailable", checks=checks)
    status = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    return ReadinessRead(status=status, checks=checks)
