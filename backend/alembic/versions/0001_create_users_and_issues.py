"""Create users and issues tables.

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("open", "in_progress", "resolved", "closed")
PRIORITIES = ("low", "medium", "high", "critical")


def _in_list(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium", nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issues")),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_issues_assignee_id_users"),
            ondelete="SET NULL",
        ),
        # Expanded by the naming convention to ck_issues_status / ck_issues_priority.
        sa.CheckConstraint(_in_list("status", STATUSES), name="status"),
        sa.CheckConstraint(_in_list("priority", PRIORITIES), name="priority"),
    )
    op.create_index(op.f("ix_issues_status"), "issues", ["status"])
    op.create_index(op.f("ix_issues_priority"), "issues", ["priority"])
    op.create_index(op.f("ix_issues_assignee_id"), "issues", ["assignee_id"])


def downgrade() -> None:
    op.drop_table("issues")
    op.drop_table("users")
