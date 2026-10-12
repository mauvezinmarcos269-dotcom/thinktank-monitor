"""add report content fetch fields

Revision ID: c3b41e5cfbd4
Revises: 13b61c27a102
Create Date: 2026-07-18 04:35:55.635361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3b41e5cfbd4'
down_revision: Union[str, Sequence[str], None] = '13b61c27a102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column(
            "crawl_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "reports",
        sa.Column(
            "content_fetched_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.add_column(
        "reports",
        sa.Column(
            "crawl_error",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_reports_crawl_status"),
        "reports",
        ["crawl_status"],
        unique=False,
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_reports_crawl_status"),
        table_name="reports",
    )

    op.execute(
        "ALTER TABLE reports DROP COLUMN IF EXISTS crawl_error"
    )
    op.execute(
        "ALTER TABLE reports "
        "DROP COLUMN IF EXISTS content_fetched_at"
    )
    op.execute(
        "ALTER TABLE reports "
        "DROP COLUMN IF EXISTS crawl_status"
    )
