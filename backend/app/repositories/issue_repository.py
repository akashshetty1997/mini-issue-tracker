from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Issue
from app.repositories.queries import PageRequest, PageResult


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

    def list(self, page: PageRequest) -> PageResult[Issue]:
        stmt = (
            select(Issue)
            .options(joinedload(Issue.assignee))
            .order_by(Issue.created_at.desc(), Issue.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        total = self._session.scalar(select(func.count()).select_from(Issue)) or 0
        return PageResult(items=self._session.scalars(stmt).all(), total=total)

    def update(self, issue_id: int, values: Mapping[str, Any]) -> bool:
        stmt = update(Issue).where(Issue.id == issue_id).values(**values)
        result = cast(CursorResult[Any], self._session.execute(stmt))
        return result.rowcount > 0

    def delete(self, issue_id: int) -> bool:
        result = cast(
            CursorResult[Any], self._session.execute(delete(Issue).where(Issue.id == issue_id))
        )
        return result.rowcount > 0
