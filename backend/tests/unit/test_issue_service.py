import pytest

from app.core.constants import IssuePriority, IssueStatus
from app.core.exceptions import (
    InvalidAssigneeError,
    InvalidStatusTransitionError,
    IssueNotFoundError,
)
from app.repositories.queries import IssueFilters, PageRequest, SortOrder
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.issue_service import IssueService
from app.services.status_policy import StatusTransitionPolicy
from tests.fakes import (
    FailingUpdateIssueRepository,
    FakeUnitOfWork,
    FixedClock,
    InMemoryIssueRepository,
    InMemoryUserLookup,
)

KNOWN_USER_ID = 7
UNKNOWN_USER_ID = 999


@pytest.fixture
def repo() -> InMemoryIssueRepository:
    return InMemoryIssueRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def service(repo: InMemoryIssueRepository, uow: FakeUnitOfWork, clock: FixedClock) -> IssueService:
    return IssueService(
        issues=repo,
        users=InMemoryUserLookup({KNOWN_USER_ID}),
        uow=uow,
        clock=clock,
        status_policy=StatusTransitionPolicy(),
    )


def make_issue(service: IssueService, **overrides: object) -> int:
    data = {"title": "Crash on save", **overrides}
    return service.create_issue(IssueCreate.model_validate(data)).id


class TestCreate:
    def test_applies_defaults_and_timestamps(
        self, service: IssueService, uow: FakeUnitOfWork, clock: FixedClock
    ) -> None:
        issue = service.create_issue(IssueCreate(title="Crash on save"))

        assert issue.status is IssueStatus.OPEN
        assert issue.priority is IssuePriority.MEDIUM
        assert issue.description == ""
        assert issue.created_at == issue.updated_at == clock.now()
        assert uow.commits == 1

    def test_with_existing_assignee(self, service: IssueService) -> None:
        issue = service.create_issue(IssueCreate(title="Crash", assignee_id=KNOWN_USER_ID))

        assert issue.assignee_id == KNOWN_USER_ID

    def test_with_unknown_assignee_is_rejected_and_nothing_is_saved(
        self, service: IssueService, repo: InMemoryIssueRepository, uow: FakeUnitOfWork
    ) -> None:
        with pytest.raises(InvalidAssigneeError):
            service.create_issue(IssueCreate(title="Crash", assignee_id=UNKNOWN_USER_ID))

        assert repo.rows == {}
        assert uow.commits == 0


class TestRead:
    def test_get_returns_issue(self, service: IssueService) -> None:
        issue_id = make_issue(service)

        assert service.get_issue(issue_id).title == "Crash on save"

    def test_get_missing_issue_raises_not_found(self, service: IssueService) -> None:
        with pytest.raises(IssueNotFoundError):
            service.get_issue(123)

    def test_list_returns_newest_first_with_total(
        self, service: IssueService, clock: FixedClock
    ) -> None:
        first = make_issue(service, title="first")
        clock.advance(minutes=1)
        second = make_issue(service, title="second")

        page = service.list_issues(
            IssueFilters(), SortOrder.parse("-created_at"), PageRequest(limit=10, offset=0)
        )

        assert [i.id for i in page.items] == [second, first]
        assert page.total == 2


class TestUpdate:
    def test_changes_only_provided_fields_and_bumps_updated_at(
        self, service: IssueService, clock: FixedClock
    ) -> None:
        issue_id = make_issue(service, description="original", priority="low")
        created_at = service.get_issue(issue_id).created_at
        clock.advance(minutes=5)

        updated = service.update_issue(issue_id, IssueUpdate(title="Renamed"))

        assert updated.title == "Renamed"
        assert updated.description == "original"
        assert updated.priority is IssuePriority.LOW
        assert updated.created_at == created_at
        assert updated.updated_at == clock.now() != created_at

    def test_allowed_status_change(self, service: IssueService) -> None:
        issue_id = make_issue(service)

        updated = service.update_issue(issue_id, IssueUpdate(status=IssueStatus.IN_PROGRESS))

        assert updated.status is IssueStatus.IN_PROGRESS

    def test_setting_the_same_status_is_allowed(self, service: IssueService) -> None:
        issue_id = make_issue(service, status="closed")

        updated = service.update_issue(issue_id, IssueUpdate(status=IssueStatus.CLOSED))

        assert updated.status is IssueStatus.CLOSED

    def test_disallowed_status_change_is_rejected_without_commit(
        self, service: IssueService, uow: FakeUnitOfWork
    ) -> None:
        issue_id = make_issue(service, status="closed")
        commits_before = uow.commits

        with pytest.raises(InvalidStatusTransitionError):
            service.update_issue(issue_id, IssueUpdate(status=IssueStatus.IN_PROGRESS))

        assert service.get_issue(issue_id).status is IssueStatus.CLOSED
        assert uow.commits == commits_before

    def test_unassign_with_null(self, service: IssueService) -> None:
        issue_id = make_issue(service, assignee_id=KNOWN_USER_ID)

        updated = service.update_issue(issue_id, IssueUpdate(assignee_id=None))

        assert updated.assignee_id is None

    def test_unknown_assignee_is_rejected(self, service: IssueService) -> None:
        issue_id = make_issue(service)

        with pytest.raises(InvalidAssigneeError):
            service.update_issue(issue_id, IssueUpdate(assignee_id=UNKNOWN_USER_ID))

    def test_missing_issue_raises_not_found(self, service: IssueService) -> None:
        with pytest.raises(IssueNotFoundError):
            service.update_issue(404, IssueUpdate(title="x"))

    def test_failure_mid_operation_rolls_back_and_never_commits(
        self, uow: FakeUnitOfWork, clock: FixedClock
    ) -> None:
        repo = FailingUpdateIssueRepository()
        service = IssueService(
            issues=repo,
            users=InMemoryUserLookup(set()),
            uow=uow,
            clock=clock,
            status_policy=StatusTransitionPolicy(),
        )
        issue_id = make_issue(service)
        commits_before = uow.commits

        with pytest.raises(RuntimeError):
            service.update_issue(issue_id, IssueUpdate(title="never saved"))

        assert uow.commits == commits_before
        assert uow.rollbacks == 1


class TestDelete:
    def test_removes_issue(
        self, service: IssueService, repo: InMemoryIssueRepository, uow: FakeUnitOfWork
    ) -> None:
        issue_id = make_issue(service)

        service.delete_issue(issue_id)

        assert issue_id not in repo.rows
        assert uow.commits == 2  # create + delete

    def test_missing_issue_raises_not_found_without_commit(
        self, service: IssueService, uow: FakeUnitOfWork
    ) -> None:
        with pytest.raises(IssueNotFoundError):
            service.delete_issue(404)

        assert uow.commits == 0
