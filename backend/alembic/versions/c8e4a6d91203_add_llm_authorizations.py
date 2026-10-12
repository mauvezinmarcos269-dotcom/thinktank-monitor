"""Add explicit LLM authorizations without granting historical reports.

Revision ID: c8e4a6d91203
Revises: b23c7a91e8d4
"""

import sqlalchemy as sa
from alembic import op

revision = "c8e4a6d91203"
down_revision = "b23c7a91e8d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crawl_candidates", sa.Column("document_hash", sa.String(64)))
    op.add_column("crawl_candidates", sa.Column("content_length", sa.Integer()))
    op.create_table(
        "llm_authorizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("target_key", sa.String(64), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("crawl_candidates.id", ondelete="SET NULL")),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id", ondelete="SET NULL")),
        sa.Column("granted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("revoked_at", sa.DateTime()),
        sa.CheckConstraint("scope IN ('relevance_sample', 'report_generation')", name="ck_llm_authorizations_scope"),
    )
    op.create_index("ix_llm_authorizations_target", "llm_authorizations", ["scope", "target_key"])


def downgrade() -> None:
    op.drop_index("ix_llm_authorizations_target", table_name="llm_authorizations")
    op.drop_table("llm_authorizations")
    op.drop_column("crawl_candidates", "content_length")
    op.drop_column("crawl_candidates", "document_hash")
