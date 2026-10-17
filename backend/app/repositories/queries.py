"""Plain value objects describing what to read, independent of HTTP and SQL."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.constants import SORT_DESC_PREFIX, IssuePriority, IssueStatus


@dataclass(frozen=True, slots=True)
class IssueFilters:
    """All criteria are combined with AND; multiple values within one criterion with OR."""

    statuses: tuple[IssueStatus, ...] = ()
    priorities: tuple[IssuePriority, ...] = ()
    assignee_id: int | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class SortOrder:
    field: str
    descending: bool

    @classmethod
    def parse(cls, value: str) -> "SortOrder":
        """``"-created_at"`` -> created_at descending, ``"title"`` -> title ascending."""
        return cls(
            field=value.removeprefix(SORT_DESC_PREFIX),
            descending=value.startswith(SORT_DESC_PREFIX),
        )


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class PageResult[T]:
    items: Sequence[T]
    total: int
