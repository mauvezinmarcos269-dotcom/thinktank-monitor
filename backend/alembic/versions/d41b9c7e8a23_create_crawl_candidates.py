"""create crawl candidates

Revision ID: d41b9c7e8a23
Revises: b7c3e9f2a8d1
Create Date: 2026-09-09 17:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d41b9c7e8a23"
down_revision: str | Sequence[str] | None = "b7c3e9f2a8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "crawl_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crawl_run_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("skip_reason_code", sa.String(length=80), nullable=True),
        sa.Column("skip_reason_label", sa.String(length=120), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("relevance", sa.String(length=30), nullable=True),
        sa.Column("relevance_reason", sa.Text(), nullable=True),
        sa.Column("is_china_related", sa.Boolean(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("non_empty_page_count", sa.Integer(), nullable=True),
        sa.Column("pdf_byte_length", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_candidates_crawl_run_id"), "crawl_candidates", ["crawl_run_id"])
    op.create_index(op.f("ix_crawl_candidates_id"), "crawl_candidates", ["id"])
    op.create_index(op.f("ix_crawl_candidates_report_id"), "crawl_candidates", ["report_id"])
    op.create_index(
        "ix_crawl_candidates_run_status",
        "crawl_candidates",
        ["crawl_run_id", "status"],
    )
    op.create_index(
        "ix_crawl_candidates_source_created",
        "crawl_candidates",
        ["source_id", "created_at"],
    )
    op.create_index(op.f("ix_crawl_candidates_skip_reason_code"), "crawl_candidates", ["skip_reason_code"])
    op.create_index(op.f("ix_crawl_candidates_source_id"), "crawl_candidates", ["source_id"])
    op.create_index(op.f("ix_crawl_candidates_status"), "crawl_candidates", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_crawl_candidates_status"), table_name="crawl_candidates")
    op.drop_index(op.f("ix_crawl_candidates_source_id"), table_name="crawl_candidates")
    op.drop_index(op.f("ix_crawl_candidates_skip_reason_code"), table_name="crawl_candidates")
    op.drop_index("ix_crawl_candidates_source_created", table_name="crawl_candidates")
    op.drop_index("ix_crawl_candidates_run_status", table_name="crawl_candidates")
    op.drop_index(op.f("ix_crawl_candidates_report_id"), table_name="crawl_candidates")
    op.drop_index(op.f("ix_crawl_candidates_id"), table_name="crawl_candidates")
    op.drop_index(op.f("ix_crawl_candidates_crawl_run_id"), table_name="crawl_candidates")
    op.drop_table("crawl_candidates")
