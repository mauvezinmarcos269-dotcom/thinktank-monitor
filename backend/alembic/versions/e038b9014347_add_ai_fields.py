"""add ai fields

Revision ID: e038b9014347
Revises: c3b41e5cfbd4
Create Date: 2026-08-10 12:55:11.086031

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e038b9014347"
down_revision: str | Sequence[str] | None = "c3b41e5cfbd4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _report_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("reports")}


def upgrade() -> None:
    """Upgrade schema."""
    existing_columns = _report_columns()

    for column in (
        sa.Column("translation", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("commentary", sa.Text(), nullable=True),
        sa.Column("ai_generated_at", sa.DateTime(), nullable=True),
    ):
        if column.name not in existing_columns:
            op.add_column("reports", column)

    if "ai_status" not in existing_columns:
        op.add_column(
            "reports",
            sa.Column(
                "ai_status",
                sa.String(length=30),
                nullable=False,
                server_default="pending",
            ),
        )
        return

    op.execute(
        "UPDATE reports SET ai_status = 'pending' WHERE ai_status IS NULL"
    )
    op.alter_column(
        "reports",
        "ai_status",
        existing_type=sa.String(length=30),
        nullable=False,
        server_default="pending",
    )


def downgrade() -> None:
    """Downgrade schema."""
    existing_columns = _report_columns()
    for column_name in (
        "ai_generated_at",
        "ai_status",
        "commentary",
        "summary",
        "translation",
    ):
        if column_name in existing_columns:
            op.drop_column("reports", column_name)
