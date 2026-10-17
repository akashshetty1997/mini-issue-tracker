"""Seed demo data. Safe to run on every start.

Users are upserted by email. Demo issues are only created on a fresh database (no users
existed before this run), so issues a user deletes don't reappear after a restart.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.constants import IssuePriority, IssueStatus
from app.core.logging import configure_logging
from app.db.session import create_db_engine, create_session_factory
from app.models import Issue, User

logger = logging.getLogger(__name__)

DEMO_USERS = (
    ("Ada Lovelace", "ada@example.com"),
    ("Alan Turing", "alan@example.com"),
    ("Grace Hopper", "grace@example.com"),
    ("Linus Torvalds", "linus@example.com"),
)

# (title, description, status, priority, assignee email or None)
DEMO_ISSUES = (
    (
        "Login page returns 500 on empty password",
        "Submitting the login form without a password crashes the auth handler.",
        IssueStatus.OPEN,
        IssuePriority.CRITICAL,
        "ada@example.com",
    ),
    (
        "Add pagination to the audit log",
        "The audit log page loads every row at once and is slow for large tenants.",
        IssueStatus.IN_PROGRESS,
        IssuePriority.MEDIUM,
        "alan@example.com",
    ),
    (
        "Typo in onboarding email",
        "'Welcom' should read 'Welcome' in the first onboarding email.",
        IssueStatus.RESOLVED,
        IssuePriority.LOW,
        "grace@example.com",
    ),
    (
        "Dark mode contrast on badges",
        "Status badges fail WCAG AA contrast in dark mode.",
        IssueStatus.OPEN,
        IssuePriority.HIGH,
        None,
    ),
    (
        "Upgrade Postgres driver",
        "Move to the latest psycopg release.",
        IssueStatus.CLOSED,
        IssuePriority.LOW,
        "linus@example.com",
    ),
)


def seed(session: Session) -> None:
    existing = {user.email: user for user in session.scalars(select(User))}
    fresh_database = not existing

    for name, email in DEMO_USERS:
        if email not in existing:
            user = User(name=name, email=email)
            session.add(user)
            existing[email] = user
    session.flush()

    if fresh_database:
        now = SystemClock().now()
        for title, description, status, priority, assignee_email in DEMO_ISSUES:
            assignee = existing[assignee_email] if assignee_email else None
            session.add(
                Issue(
                    title=title,
                    description=description,
                    status=status,
                    priority=priority,
                    assignee_id=assignee.id if assignee else None,
                    created_at=now,
                    updated_at=now,
                )
            )
    session.commit()
    logger.info("Seed complete", extra={"fresh_database": fresh_database})


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)
    try:
        with create_session_factory(engine)() as session:
            seed(session)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
