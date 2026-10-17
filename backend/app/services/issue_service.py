from app.core.clock import Clock
from app.core.exceptions import InvalidAssigneeError, IssueNotFoundError, VersionConflictError
from app.models import Issue
from app.repositories.interfaces import IssueRepository, UnitOfWork, UserLookup
from app.repositories.queries import IssueFilters, PageRequest, PageResult, SortOrder
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.status_policy import StatusTransitionPolicy


class IssueService:
    """Issue use cases and the business rules around them.

    Depends only on abstractions (repository protocols, unit of work, clock, policy), so it
    can be exercised in unit tests without a database or HTTP.
    """

    def __init__(
        self,
        *,
        issues: IssueRepository,
        users: UserLookup,
        uow: UnitOfWork,
        clock: Clock,
        status_policy: StatusTransitionPolicy,
    ) -> None:
        self._issues = issues
        self._users = users
        self._uow = uow
        self._clock = clock
        self._status_policy = status_policy

    def get_issue(self, issue_id: int) -> Issue:
        issue = self._issues.get(issue_id)
        if issue is None:
            raise IssueNotFoundError(issue_id)
        return issue

    def list_issues(
        self, filters: IssueFilters, sort: SortOrder, page: PageRequest
    ) -> PageResult[Issue]:
        return self._issues.list(filters, sort, page)

    def create_issue(self, data: IssueCreate) -> Issue:
        with self._uow:
            if data.assignee_id is not None:
                self._ensure_assignee_exists(data.assignee_id)
            now = self._clock.now()
            issue = self._issues.add(Issue(**data.model_dump(), created_at=now, updated_at=now))
            created = self.get_issue(issue.id)
            self._uow.commit()
        return created

    def update_issue(self, issue_id: int, data: IssueUpdate) -> Issue:
        changes = data.model_dump(exclude_unset=True, exclude={"version"})
        with self._uow:
            issue = self.get_issue(issue_id)
            # Fail fast with a clear error; the conditional UPDATE below closes the race.
            if issue.version != data.version:
                raise VersionConflictError(data.version, issue.version)
            if "status" in changes:
                self._status_policy.ensure_can_transition(issue.status, changes["status"])
            if changes.get("assignee_id") is not None:
                self._ensure_assignee_exists(changes["assignee_id"])

            changes["updated_at"] = self._clock.now()
            if not self._issues.update(issue_id, changes, expected_version=data.version):
                # Another request deleted or changed the issue after we read it.
                if self._issues.get(issue_id) is None:
                    raise IssueNotFoundError(issue_id)
                raise VersionConflictError(data.version)
            updated = self.get_issue(issue_id)
            self._uow.commit()
        return updated

    def delete_issue(self, issue_id: int) -> None:
        with self._uow:
            if not self._issues.delete(issue_id):
                raise IssueNotFoundError(issue_id)
            self._uow.commit()

    def _ensure_assignee_exists(self, user_id: int) -> None:
        if not self._users.exists(user_id):
            raise InvalidAssigneeError(user_id)
