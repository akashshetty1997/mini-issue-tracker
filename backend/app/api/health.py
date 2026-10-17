"""Infrastructure probes. Unversioned: they describe the process, not the API contract."""

import logging

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep
from app.schemas.meta import HealthRead, ReadinessRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> HealthRead:
    return HealthRead(status="ok")


@router.get("/ready", summary="Readiness probe (checks the database)")
def ready(session: SessionDep, response: Response) -> ReadinessRead:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness check failed: database unavailable", exc_info=True)
        response.status_code = 503
        return ReadinessRead(status="unavailable", checks={"database": "unavailable"})
    return ReadinessRead(status="ready", checks={"database": "ok"})
