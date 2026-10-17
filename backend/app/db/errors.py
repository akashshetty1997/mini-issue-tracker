"""Translate database constraint violations into domain errors.

The service validates input before writing (e.g. that the assignee exists), but another
request can change the data between that check and the INSERT. When the database
rejects the write, the client should still get a meaningful 4xx error, not a 5xx.
"""

from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    ASSIGNEE_FK_CONSTRAINT,
    PG_FOREIGN_KEY_VIOLATION,
    PG_UNIQUE_VIOLATION,
)
from app.core.exceptions import AppError, ConflictError, InvalidAssigneeError


def translate_integrity_error(exc: IntegrityError) -> AppError | None:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)

    if sqlstate == PG_FOREIGN_KEY_VIOLATION and constraint == ASSIGNEE_FK_CONSTRAINT:
        return InvalidAssigneeError()
    if sqlstate in (PG_FOREIGN_KEY_VIOLATION, PG_UNIQUE_VIOLATION):
        return ConflictError()
    return None
