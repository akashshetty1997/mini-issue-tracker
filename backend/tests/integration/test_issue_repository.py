"""Repository behaviour that only the real database can prove."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Issue
from app.repositories.issue_repository import SqlAlchemyIssueRepository


def test_conditional_update_applies_only_at_the_expected_version(db_session: Session) -> None:
    repo = SqlAlchemyIssueRepository(db_session)
    now = datetime.now(UTC)
    issue = repo.add(Issue(title="original", created_at=now, updated_at=now))

    first = repo.update(issue.id, {"title": "first writer"}, expected_version=1)
    second = repo.update(issue.id, {"title": "second writer"}, expected_version=1)

    stored = repo.get(issue.id)
    assert (first, second) == (True, False)
    assert stored is not None
    assert stored.title == "first writer"
    assert stored.version == 2


def test_update_of_missing_issue_reports_no_row(db_session: Session) -> None:
    repo = SqlAlchemyIssueRepository(db_session)

    assert repo.update(999_999, {"title": "x"}, expected_version=1) is False
