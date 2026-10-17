"""Application-wide constants.

Every fixed value the application relies on lives here. Values that change between
environments (URLs, credentials, pool sizes) belong in ``app.core.config`` instead.
"""

import re
from enum import StrEnum
from types import MappingProxyType
from typing import Final

# --- API -------------------------------------------------------------------------------
APP_TITLE: Final = "Mini Issue Tracker API"
APP_VERSION: Final = "1.0.0"
API_V1_PREFIX: Final = "/api/v1"


# --- Issue domain ----------------------------------------------------------------------
class IssueStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssuePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


DEFAULT_STATUS: Final = IssueStatus.OPEN
DEFAULT_PRIORITY: Final = IssuePriority.MEDIUM

# Which statuses an issue may move to from its current status. Moving to the same status
# is always a no-op and is not listed. Closed issues must be reopened before work resumes.
STATUS_TRANSITIONS: Final = MappingProxyType(
    {
        IssueStatus.OPEN: frozenset(
            {IssueStatus.IN_PROGRESS, IssueStatus.RESOLVED, IssueStatus.CLOSED}
        ),
        IssueStatus.IN_PROGRESS: frozenset(
            {IssueStatus.OPEN, IssueStatus.RESOLVED, IssueStatus.CLOSED}
        ),
        IssueStatus.RESOLVED: frozenset(
            {IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.CLOSED}
        ),
        IssueStatus.CLOSED: frozenset({IssueStatus.OPEN}),
    }
)

# Sorting by priority must follow severity, not alphabetical order.
PRIORITY_RANK: Final = MappingProxyType(
    {
        IssuePriority.LOW: 0,
        IssuePriority.MEDIUM: 1,
        IssuePriority.HIGH: 2,
        IssuePriority.CRITICAL: 3,
    }
)

# --- Field limits ----------------------------------------------------------------------
TITLE_MIN_LENGTH: Final = 1
TITLE_MAX_LENGTH: Final = 200
DESCRIPTION_MAX_LENGTH: Final = 10_000
USER_NAME_MAX_LENGTH: Final = 100
EMAIL_MAX_LENGTH: Final = 255
ENUM_COLUMN_LENGTH: Final = 20
# Upper bound of a Postgres INTEGER; larger ids would otherwise surface as database errors.
MAX_DB_INT: Final = 2_147_483_647

# --- Listing ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE: Final = 20
MAX_PAGE_SIZE: Final = 100
SEARCH_MAX_LENGTH: Final = 200
SORTABLE_FIELDS: Final = ("created_at", "updated_at", "priority", "title")
DEFAULT_SORT: Final = "-created_at"
SORT_DESC_PREFIX: Final = "-"
LIKE_ESCAPE_CHAR: Final = "\\"


# --- Errors ----------------------------------------------------------------------------
class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ISSUE_NOT_FOUND = "ISSUE_NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INVALID_ASSIGNEE = "INVALID_ASSIGNEE"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    CONFLICT = "CONFLICT"
    HTTP_ERROR = "HTTP_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Postgres SQLSTATE codes we translate into domain errors.
PG_FOREIGN_KEY_VIOLATION: Final = "23503"
PG_UNIQUE_VIOLATION: Final = "23505"
ASSIGNEE_FK_CONSTRAINT: Final = "fk_issues_assignee_id_users"

# --- HTTP headers ----------------------------------------------------------------------
REQUEST_ID_HEADER: Final = "X-Request-ID"
# Incoming request ids are only trusted if they match this; anything else is replaced so
# client-controlled values can't inject content into log lines.
REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
CORS_EXPOSED_HEADERS: Final = (REQUEST_ID_HEADER, "Location")
CORS_ALLOWED_METHODS: Final = ("GET", "POST", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOWED_HEADERS: Final = ("Content-Type", REQUEST_ID_HEADER)
