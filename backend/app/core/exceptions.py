"""Domain errors.

Each error carries its HTTP status and error code, so a single handler can render any of
them. Adding a new error means adding a subclass; no handler changes are needed.
"""

from collections.abc import Iterable
from typing import Any, ClassVar

from app.core.constants import ErrorCode, IssueStatus


class AppError(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[ErrorCode] = ErrorCode.INTERNAL_ERROR
    default_message: ClassVar[str] = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND
    default_message = "The requested resource was not found."


class IssueNotFoundError(NotFoundError):
    code = ErrorCode.ISSUE_NOT_FOUND

    def __init__(self, issue_id: int) -> None:
        super().__init__(f"Issue {issue_id} was not found.")


class InvalidAssigneeError(AppError):
    status_code = 422
    code = ErrorCode.INVALID_ASSIGNEE

    def __init__(self, assignee_id: int | None = None) -> None:
        message = (
            f"User {assignee_id} does not exist."
            if assignee_id is not None
            else "The selected assignee does not exist."
        )
        super().__init__(message, details=[{"field": "assignee_id", "message": message}])


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT
    default_message = "The request conflicts with the current state of the resource."


class InvalidStatusTransitionError(ConflictError):
    code = ErrorCode.INVALID_STATUS_TRANSITION

    def __init__(
        self, current: IssueStatus, target: IssueStatus, allowed: Iterable[IssueStatus]
    ) -> None:
        allowed_values = [status.value for status in allowed]
        super().__init__(
            f"Cannot change status from '{current.value}' to '{target.value}'.",
            details={"from": current.value, "to": target.value, "allowed": allowed_values},
        )
