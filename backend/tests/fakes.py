"""In-memory stand-ins for the persistence ports, used by service unit tests.

They implement the same Protocols as the SQLAlchemy classes, which is what lets the real
IssueService run unchanged without a database.
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Any, Self

from app.core.constants import PRIORITY_RANK
from app.models import Issue
from app.repositories.queries import IssueFilters, PageRequest, PageResult, SortOrder


class FixedClock:
    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class InMemoryIssueRepository:
    def __init__(self) -> None:
        self.rows: dict[int, Issue] = {}
        self._next_id = 1

    def add(self, issue: Issue) -> Issue:
        issue.id = self._next_id
        self._next_id += 1
        self.rows[issue.id] = issue
        return issue

    def get(self, issue_id: int) -> Issue | None:
        return self.rows.get(issue_id)

    def list(self, filters: IssueFilters, sort: SortOrder, page: PageRequest) -> PageResult[Issue]:
        matching = [issue for issue in self.rows.values() if self._matches(issue, filters)]

        def sort_key(issue: Issue) -> tuple[Any, int]:
            value = getattr(issue, sort.field)
            return (PRIORITY_RANK[value] if sort.field == "priority" else value, issue.id)

        ordered = sorted(matching, key=sort_key, reverse=sort.descending)
        return PageResult(items=ordered[page.offset : page.offset + page.limit], total=len(ordered))

    @staticmethod
    def _matches(issue: Issue, filters: IssueFilters) -> bool:
        term = (filters.search or "").lower()
        return (
            (not filters.statuses or issue.status in filters.statuses)
            and (not filters.priorities or issue.priority in filters.priorities)
            and (filters.assignee_id is None or issue.assignee_id == filters.assignee_id)
            and (not term or term in issue.title.lower() or term in issue.description.lower())
        )

    def update(self, issue_id: int, values: Mapping[str, Any]) -> bool:
        issue = self.rows.get(issue_id)
        if issue is None:
            return False
        for field, value in values.items():
            setattr(issue, field, value)
        return True

    def delete(self, issue_id: int) -> bool:
        return self.rows.pop(issue_id, None) is not None


class FailingUpdateIssueRepository(InMemoryIssueRepository):
    """Simulates the database failing part-way through an update."""

    def update(self, issue_id: int, values: Mapping[str, Any]) -> bool:
        raise RuntimeError("simulated database failure")


class InMemoryUserLookup:
    def __init__(self, user_ids: set[int]) -> None:
        self.user_ids = user_ids

    def exists(self, user_id: int) -> bool:
        return user_id in self.user_ids


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is not None:
            self.rollbacks += 1

    def commit(self) -> None:
        self.commits += 1
