from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    ENUM_COLUMN_LENGTH,
    INITIAL_VERSION,
    TITLE_MAX_LENGTH,
    IssuePriority,
    IssueStatus,
)
from app.db.base import Base
from app.models.user import User


def _string_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    # Stored as VARCHAR + CHECK constraint instead of a native Postgres ENUM, so adding a
    # value later is a simple constraint change rather than an ALTER TYPE.
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=ENUM_COLUMN_LENGTH,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[IssueStatus] = mapped_column(
        _string_enum(IssueStatus, "status"),
        default=DEFAULT_STATUS,
        server_default=DEFAULT_STATUS.value,
    )
    priority: Mapped[IssuePriority] = mapped_column(
        _string_enum(IssuePriority, "priority"),
        default=DEFAULT_PRIORITY,
        server_default=DEFAULT_PRIORITY.value,
        index=True,
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Set by the service through an injected Clock; the server defaults are a backstop for
    # rows written outside the application.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Optimistic-locking counter: bumped on every update; writers must name the version
    # they read, so concurrent edits are detected instead of silently overwritten.
    version: Mapped[int] = mapped_column(
        default=INITIAL_VERSION, server_default=str(INITIAL_VERSION)
    )

    assignee: Mapped[User | None] = relationship()


# List-query indexes (migration 0002). They match the default sort, created_at DESC with
# id as tiebreaker, with and without a status filter. The status-led index also serves
# plain status lookups, so status has no single-column index.
Index("ix_issues_created_at_id", Issue.created_at.desc(), Issue.id.desc())
Index("ix_issues_status_created_at_id", Issue.status, Issue.created_at.desc(), Issue.id.desc())
# Trigram indexes let ILIKE '%term%' searches use an index (for terms of 3+ characters).
Index(
    "ix_issues_title_trgm",
    Issue.title,
    postgresql_using="gin",
    postgresql_ops={"title": "gin_trgm_ops"},
)
Index(
    "ix_issues_description_trgm",
    Issue.description,
    postgresql_using="gin",
    postgresql_ops={"description": "gin_trgm_ops"},
)
