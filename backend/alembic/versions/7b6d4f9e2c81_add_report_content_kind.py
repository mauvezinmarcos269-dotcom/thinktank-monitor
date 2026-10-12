"""Add report content kind fields.

Revision ID: 7b6d4f9e2c81
Revises: 4e2c9b7a1d30
Create Date: 2026-09-11 21:07:30.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7b6d4f9e2c81"
down_revision: str | None = "4e2c9b7a1d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "content_kind",
            sa.String(length=30),
            nullable=False,
            server_default="pdf",
        ),
    )
    op.create_index(
        op.f("ix_reports_content_kind"),
        "reports",
        ["content_kind"],
        unique=False,
    )
    op.execute(
        """
        UPDATE reports
        SET content_kind = 'web_article'
        WHERE pdf_url IS NULL
          AND page_count IS NULL
          AND content IS NOT NULL
        """
    )

    op.add_column(
        "crawl_candidates",
        sa.Column(
            "content_kind",
            sa.String(length=30),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_crawl_candidates_content_kind"),
        "crawl_candidates",
        ["content_kind"],
        unique=False,
    )
    op.execute(
        """
        UPDATE crawl_candidates
        SET content_kind = 'web_article'
        WHERE status = 'saved'
          AND pdf_url IS NULL
          AND page_count IS NULL
        """
    )
    op.execute(
        """
        UPDATE crawl_candidates
        SET content_kind = 'pdf'
        WHERE pdf_url IS NOT NULL
           OR page_count IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_crawl_candidates_content_kind"),
        table_name="crawl_candidates",
    )
    op.drop_column(
        "crawl_candidates",
        "content_kind",
    )

    op.drop_index(
        op.f("ix_reports_content_kind"),
        table_name="reports",
    )
    op.drop_column(
        "reports",
        "content_kind",
    )
