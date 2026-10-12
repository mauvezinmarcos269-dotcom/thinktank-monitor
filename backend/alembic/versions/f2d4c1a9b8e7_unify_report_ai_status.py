"""unify report ai status

Revision ID: f2d4c1a9b8e7
Revises: e038b9014347
Create Date: 2026-08-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2d4c1a9b8e7"
down_revision: str | Sequence[str] | None = "e038b9014347"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column(
            "ai_retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.drop_column("reports", "analysis_status")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "reports",
        sa.Column(
            "analysis_status",
            sa.String(length=30),
            nullable=True,
        ),
    )
    op.drop_column("reports", "ai_retry_count")
