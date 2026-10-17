"""Persistence ports the service layer depends on.

The service only knows these Protocols. SQLAlchemy implementations are wired in by
``app.api.deps``; tests substitute in-memory fakes.
"""

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any, Protocol, Self

from app.models import Issue, User
from app.repositories.queries import PageRequest, PageResult


class IssueRepository(Protocol):
    def add(self, issue: Issue) -> Issue: ...

    def get(self, issue_id: int) -> Issue | None: ...

    def list(self, page: PageRequest) -> PageResult[Issue]: ...

    def update(self, issue_id: int, values: Mapping[str, Any]) -> bool:
        """Apply ``values`` to the issue. Returns False if no row was updated."""
        ...

    def delete(self, issue_id: int) -> bool:
        """Delete the issue. Returns False if it did not exist."""
        ...


class UserLookup(Protocol):
    """The only thing the issue service needs to know about users."""

    def exists(self, user_id: int) -> bool: ...


class UserDirectory(Protocol):
    def list_all(self) -> Sequence[User]: ...


class UnitOfWork(Protocol):
    """Transaction boundary. Nothing is persisted unless ``commit`` is called; leaving the
    block, normally or through an exception, discards uncommitted work."""

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
