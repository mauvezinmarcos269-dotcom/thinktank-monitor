"""add report review status

Revision ID: 9a1f3d2c4b70
Revises: 7b6d4f9e2c81
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "9a1f3d2c4b70"
down_revision: str | None = "7b6d4f9e2c81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "review_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending_review",
        ),
    )
    op.create_index(
        op.f("ix_reports_review_status"),
        "reports",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_reports_review_status"),
        table_name="reports",
    )
    op.drop_column(
        "reports",
        "review_status",
    )
