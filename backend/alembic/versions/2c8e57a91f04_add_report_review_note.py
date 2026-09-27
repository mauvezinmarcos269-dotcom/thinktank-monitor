"""add report review note

Revision ID: 2c8e57a91f04
Revises: 9a1f3d2c4b70
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "2c8e57a91f04"
down_revision: str | None = "9a1f3d2c4b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "review_note",
            sa.Text(),
            nullable=True,
        ),
    )
    op.add_column(
        "reports",
        sa.Column(
            "reviewed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("reports", "reviewed_at")
    op.drop_column("reports", "review_note")
