"""create report review events

Revision ID: 61f8a32d9c05
Revises: 2c8e57a91f04
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "61f8a32d9c05"
down_revision: str | None = "2c8e57a91f04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_review_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=30),
            server_default="pending_review",
            nullable=False,
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_review_events_created_at"),
        "report_review_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_review_events_id"),
        "report_review_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_review_events_report_id"),
        "report_review_events",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_review_events_review_status"),
        "report_review_events",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_report_review_events_review_status"),
        table_name="report_review_events",
    )
    op.drop_index(
        op.f("ix_report_review_events_report_id"),
        table_name="report_review_events",
    )
    op.drop_index(
        op.f("ix_report_review_events_id"),
        table_name="report_review_events",
    )
    op.drop_index(
        op.f("ix_report_review_events_created_at"),
        table_name="report_review_events",
    )
    op.drop_table("report_review_events")
