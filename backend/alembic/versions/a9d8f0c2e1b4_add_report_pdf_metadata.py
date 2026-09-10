"""add report pdf metadata

Revision ID: a9d8f0c2e1b4
Revises: cc55b8fca9a8
Create Date: 2026-09-07 21:58:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9d8f0c2e1b4"
down_revision: str | Sequence[str] | None = "cc55b8fca9a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column("pdf_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("non_empty_page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("pdf_byte_length", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("reports", "pdf_byte_length")
    op.drop_column("reports", "non_empty_page_count")
    op.drop_column("reports", "page_count")
    op.drop_column("reports", "pdf_url")
