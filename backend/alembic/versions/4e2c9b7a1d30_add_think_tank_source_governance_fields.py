"""add think tank source governance fields

Revision ID: 4e2c9b7a1d30
Revises: d41b9c7e8a23
Create Date: 2026-09-11 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "4e2c9b7a1d30"
down_revision: Union[str, Sequence[str], None] = "d41b9c7e8a23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    priority_tier_enum = postgresql.ENUM(
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
        name="prioritytierenum",
        create_type=False,
    )
    region_focus_enum = postgresql.ENUM(
        "us",
        "europe",
        "neighboring",
        "international",
        "domestic",
        "candidate",
        name="regionfocusenum",
        create_type=False,
    )

    bind = op.get_bind()
    priority_tier_enum.create(bind, checkfirst=True)
    region_focus_enum.create(bind, checkfirst=True)

    op.add_column(
        "think_tanks",
        sa.Column(
            "priority_tier",
            priority_tier_enum,
            nullable=False,
            server_default=sa.text("'P4'"),
        ),
    )
    op.add_column(
        "think_tanks",
        sa.Column(
            "region_focus",
            region_focus_enum,
            nullable=False,
            server_default=sa.text("'candidate'"),
        ),
    )
    op.add_column(
        "think_tanks",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_index(
        op.f("ix_think_tanks_priority_tier"),
        "think_tanks",
        ["priority_tier"],
        unique=False,
    )
    op.create_index(
        op.f("ix_think_tanks_region_focus"),
        "think_tanks",
        ["region_focus"],
        unique=False,
    )
    op.create_index(
        op.f("ix_think_tanks_is_verified"),
        "think_tanks",
        ["is_verified"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_think_tanks_is_verified"),
        table_name="think_tanks",
    )
    op.drop_index(
        op.f("ix_think_tanks_region_focus"),
        table_name="think_tanks",
    )
    op.drop_index(
        op.f("ix_think_tanks_priority_tier"),
        table_name="think_tanks",
    )

    op.drop_column("think_tanks", "is_verified")
    op.drop_column("think_tanks", "region_focus")
    op.drop_column("think_tanks", "priority_tier")

    bind = op.get_bind()
    postgresql.ENUM(name="regionfocusenum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="prioritytierenum").drop(bind, checkfirst=True)
