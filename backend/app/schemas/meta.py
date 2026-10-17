from pydantic import BaseModel

from app.core.constants import IssuePriority, IssueStatus


class FieldLimits(BaseModel):
    title_min_length: int
    title_max_length: int
    description_max_length: int
    default_page_size: int
    max_page_size: int
    search_max_length: int


class MetaRead(BaseModel):
    """Reference data so clients don't hard-code the server's rules."""

    statuses: list[IssueStatus]
    priorities: list[IssuePriority]
    status_transitions: dict[IssueStatus, list[IssueStatus]]
    limits: FieldLimits
    sortable_fields: list[str]
    default_sort: str


class HealthRead(BaseModel):
    status: str


class ReadinessRead(BaseModel):
    status: str
    checks: dict[str, str]
