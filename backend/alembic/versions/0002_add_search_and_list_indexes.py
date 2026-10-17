"""Add search (trigram) and list-ordering indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pg_trgm is a trusted extension (Postgres 13+), so the database owner can create it.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        op.f("ix_issues_title_trgm"),
        "issues",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        op.f("ix_issues_description_trgm"),
        "issues",
        ["description"],
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )

    # Match the default ordering (created_at DESC, id DESC), with and without a status
    # filter. The status-led index makes the single-column status index redundant.
    op.create_index(
        op.f("ix_issues_created_at_id"),
        "issues",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        op.f("ix_issues_status_created_at_id"),
        "issues",
        ["status", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.drop_index(op.f("ix_issues_status"), table_name="issues")


def downgrade() -> None:
    op.create_index(op.f("ix_issues_status"), "issues", ["status"])
    op.drop_index(op.f("ix_issues_status_created_at_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_created_at_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_description_trgm"), table_name="issues")
    op.drop_index(op.f("ix_issues_title_trgm"), table_name="issues")
    # The extension is left installed; other objects may depend on it.
