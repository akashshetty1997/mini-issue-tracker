from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.constants import (
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    DESCRIPTION_MAX_LENGTH,
    MAX_DB_INT,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    IssuePriority,
    IssueStatus,
)

# Whitespace is stripped before the length check, so "   " is rejected as empty.
Title = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    ),
]
Description = Annotated[str, StringConstraints(max_length=DESCRIPTION_MAX_LENGTH)]
UserId = Annotated[int, Field(gt=0, le=MAX_DB_INT)]

_NON_NULLABLE_UPDATE_FIELDS = ("title", "status", "priority")


class IssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description = ""
    status: IssueStatus = DEFAULT_STATUS
    priority: IssuePriority = DEFAULT_PRIORITY
    assignee_id: UserId | None = None


class IssueUpdate(BaseModel):
    """Partial update. Only fields present in the request body are changed.

    - title/status/priority: may be omitted, but not set to null
    - description: null is treated as an empty description
    - assignee_id: null unassigns the issue
    """

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    status: IssueStatus | None = None
    priority: IssuePriority | None = None
    assignee_id: UserId | None = None

    @field_validator(*_NON_NULLABLE_UPDATE_FIELDS, mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("This field cannot be null.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def null_description_to_empty(cls, value: Any) -> Any:
        return "" if value is None else value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "IssueUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self
