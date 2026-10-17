"""Dependency wiring: the only place concrete implementations are chosen."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import SystemClock
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.interfaces import UserDirectory
from app.repositories.issue_repository import SqlAlchemyIssueRepository
from app.repositories.user_repository import SqlAlchemyUserRepository
from app.services.issue_service import IssueService
from app.services.status_policy import DEFAULT_STATUS_POLICY


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_issue_service(session: SessionDep) -> IssueService:
    return IssueService(
        issues=SqlAlchemyIssueRepository(session),
        users=SqlAlchemyUserRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        clock=SystemClock(),
        status_policy=DEFAULT_STATUS_POLICY,
    )


def get_user_directory(session: SessionDep) -> UserDirectory:
    return SqlAlchemyUserRepository(session)


IssueServiceDep = Annotated[IssueService, Depends(get_issue_service)]
UserDirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]
