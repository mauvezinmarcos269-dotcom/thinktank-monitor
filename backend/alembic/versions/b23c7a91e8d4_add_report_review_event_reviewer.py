"""add report review event reviewer

Revision ID: b23c7a91e8d4
Revises: 61f8a32d9c05
Create Date: 2026-09-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b23c7a91e8d4"
down_revision: str | None = "61f8a32d9c05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "report_review_events",
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_report_review_events_reviewer_id"),
        "report_review_events",
        ["reviewer_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_report_review_events_reviewer_id_users"),
        "report_review_events",
        "users",
        ["reviewer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_report_review_events_reviewer_id_users"),
        "report_review_events",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_report_review_events_reviewer_id"),
        table_name="report_review_events",
    )
    op.drop_column("report_review_events", "reviewer_id")
