"""Add structured payload to notifications.

Revision ID: d9f1a2c3b4e5
Revises: c8e4a6d91203
"""

import sqlalchemy as sa

from alembic import op

revision = "d9f1a2c3b4e5"
down_revision = "c8e4a6d91203"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "payload")
