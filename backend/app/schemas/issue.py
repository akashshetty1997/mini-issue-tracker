from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_PRIORITY,
    DEFAULT_SORT,
    DEFAULT_STATUS,
    DESCRIPTION_MAX_LENGTH,
    MAX_DB_INT,
    MAX_PAGE_SIZE,
    SEARCH_MAX_LENGTH,
    SORTABLE_FIELDS,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    IssuePriority,
    IssueStatus,
)
from app.repositories.queries import IssueFilters, PageRequest, SortOrder
from app.schemas.user import UserSummary
from app.services.status_policy import DEFAULT_STATUS_POLICY

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


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: IssueStatus
    priority: IssuePriority
    assignee_id: int | None
    assignee: UserSummary | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_transitions(self) -> list[IssueStatus]:
        """Statuses this issue can move to next, so clients only offer legal changes."""
        return DEFAULT_STATUS_POLICY.allowed_from(self.status)


SearchTerm = Annotated[str, StringConstraints(strip_whitespace=True, max_length=SEARCH_MAX_LENGTH)]


class IssueListParams(BaseModel):
    """Query parameters for listing issues. Repeat ``status``/``priority`` to match any of
    several values, e.g. ``?status=open&status=in_progress``."""

    model_config = ConfigDict(extra="forbid")

    status: list[IssueStatus] = Field(default_factory=list)
    priority: list[IssuePriority] = Field(default_factory=list)
    assignee_id: UserId | None = None
    q: SearchTerm | None = Field(None, description="Case-insensitive title/description search")
    sort: str = Field(
        DEFAULT_SORT,
        description=f"One of {', '.join(SORTABLE_FIELDS)}; prefix with '-' for descending",
    )
    limit: int = Field(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(0, ge=0)

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, value: str) -> str:
        if SortOrder.parse(value).field not in SORTABLE_FIELDS:
            allowed = ", ".join(SORTABLE_FIELDS)
            raise ValueError(f"Unknown sort field. Use one of: {allowed} (prefix '-' for desc).")
        return value

    def filters(self) -> IssueFilters:
        return IssueFilters(
            statuses=tuple(self.status),
            priorities=tuple(self.priority),
            assignee_id=self.assignee_id,
            search=self.q or None,
        )

    def sort_order(self) -> SortOrder:
        return SortOrder.parse(self.sort)

    def page_request(self) -> PageRequest:
        return PageRequest(limit=self.limit, offset=self.offset)
