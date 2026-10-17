from collections.abc import Callable, Mapping
from typing import Any, cast

from sqlalchemy import (
    ColumnElement,
    CursorResult,
    case,
    delete,
    func,
    or_,
    select,
    update,
)
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload

from app.core.constants import LIKE_ESCAPE_CHAR, PRIORITY_RANK
from app.models import Issue
from app.repositories.queries import IssueFilters, PageRequest, PageResult, SortOrder


def escape_like(term: str) -> str:
    """Escape LIKE wildcards so user input is matched literally ("%" means a percent sign)."""
    return (
        term.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{LIKE_ESCAPE_CHAR}_")
    )


# Each builder turns one filter criterion into a WHERE clause, or None when it isn't set.
# Supporting a new filter means adding a builder; the query code below doesn't change.
type FilterBuilder = Callable[[IssueFilters], ColumnElement[bool] | None]


def _by_status(filters: IssueFilters) -> ColumnElement[bool] | None:
    return Issue.status.in_(filters.statuses) if filters.statuses else None


def _by_priority(filters: IssueFilters) -> ColumnElement[bool] | None:
    return Issue.priority.in_(filters.priorities) if filters.priorities else None


def _by_assignee(filters: IssueFilters) -> ColumnElement[bool] | None:
    return Issue.assignee_id == filters.assignee_id if filters.assignee_id is not None else None


def _by_search(filters: IssueFilters) -> ColumnElement[bool] | None:
    if not filters.search:
        return None
    pattern = f"%{escape_like(filters.search)}%"
    return or_(
        Issue.title.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
        Issue.description.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
    )


FILTER_BUILDERS: tuple[FilterBuilder, ...] = (_by_status, _by_priority, _by_assignee, _by_search)

SORT_COLUMNS: Mapping[str, ColumnElement[Any] | InstrumentedAttribute[Any]] = {
    "created_at": Issue.created_at,
    "updated_at": Issue.updated_at,
    "title": func.lower(Issue.title),
    # Severity order rather than alphabetical order.
    "priority": case(dict(PRIORITY_RANK), value=Issue.priority),
}


class SqlAlchemyIssueRepository:
    """All SQL for issues. Never commits: the unit of work owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, issue: Issue) -> Issue:
        self._session.add(issue)
        self._session.flush()
        return issue

    def get(self, issue_id: int) -> Issue | None:
        stmt = (
            select(Issue)
            .options(joinedload(Issue.assignee))
            .where(Issue.id == issue_id)
            # Refresh objects already in the session, e.g. right after a bulk UPDATE.
            .execution_options(populate_existing=True)
        )
        return self._session.scalars(stmt).one_or_none()

    def list(self, filters: IssueFilters, sort: SortOrder, page: PageRequest) -> PageResult[Issue]:
        clauses = [c for build in FILTER_BUILDERS if (c := build(filters)) is not None]

        sort_column = SORT_COLUMNS[sort.field]
        # `id` breaks ties so offset pagination never repeats or skips rows.
        order_by = (
            (sort_column.desc(), Issue.id.desc())
            if sort.descending
            else (sort_column.asc(), Issue.id.asc())
        )
        items_stmt = (
            select(Issue)
            .options(joinedload(Issue.assignee))
            .where(*clauses)
            .order_by(*order_by)
            .limit(page.limit)
            .offset(page.offset)
        )
        # Counted from the bare filtered table: no join, no ORDER BY.
        count_stmt = select(func.count()).select_from(Issue).where(*clauses)

        total = self._session.scalar(count_stmt) or 0
        return PageResult(items=self._session.scalars(items_stmt).all(), total=total)

    def update(self, issue_id: int, values: Mapping[str, Any]) -> bool:
        stmt = update(Issue).where(Issue.id == issue_id).values(**values)
        result = cast(CursorResult[Any], self._session.execute(stmt))
        return result.rowcount > 0

    def delete(self, issue_id: int) -> bool:
        result = cast(
            CursorResult[Any], self._session.execute(delete(Issue).where(Issue.id == issue_id))
        )
        return result.rowcount > 0
