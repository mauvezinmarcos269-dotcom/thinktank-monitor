"""create think tanks and sources

Revision ID: d6ebbf1053b2
Revises: 01962f4f75da
Create Date: 2026-07-12 22:02:26.691145
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d6ebbf1053b2"
down_revision: Union[str, Sequence[str], None] = "01962f4f75da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    organization_type_enum = postgresql.ENUM(
        "think_tank",
        "research_association",
        "research_institute",
        "foundation",
        "international_organization",
        name="organizationtypeenum",
        create_type=False,
    )

    source_type_enum = postgresql.ENUM(
        "website",
        "rss",
        "report_library",
        "topic_page",
        name="sourcetypeenum",
        create_type=False,
    )

    crawl_status_enum = postgresql.ENUM(
        "never",
        "running",
        "success",
        "failed",
        name="crawlstatusenum",
        create_type=False,
    )

    bind = op.get_bind()

    organization_type_enum.create(bind, checkfirst=True)
    source_type_enum.create(bind, checkfirst=True)
    crawl_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "think_tanks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "organization_type",
            organization_type_enum,
            nullable=False,
            server_default=sa.text("'think_tank'"),
        ),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_key",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["think_tanks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_think_tanks_id"),
        "think_tanks",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_name"),
        "think_tanks",
        ["name"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_name_en"),
        "think_tanks",
        ["name_en"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_country"),
        "think_tanks",
        ["country"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_parent_id"),
        "think_tanks",
        ["parent_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_is_key"),
        "think_tanks",
        ["is_key"],
        unique=False,
    )

    op.create_index(
        op.f("ix_think_tanks_is_active"),
        "think_tanks",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("think_tank_id", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            source_type_enum,
            nullable=False,
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column(
            "crawl_frequency_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1440"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "last_crawl_status",
            crawl_status_enum,
            nullable=False,
            server_default=sa.text("'never'"),
        ),
        sa.Column(
            "last_crawled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["think_tank_id"],
            ["think_tanks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "url",
            name="uq_sources_url",
        ),
    )

    op.create_index(
        op.f("ix_sources_id"),
        "sources",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_sources_think_tank_id"),
        "sources",
        ["think_tank_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_sources_is_active"),
        "sources",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_sources_is_active"),
        table_name="sources",
    )

    op.drop_index(
        op.f("ix_sources_think_tank_id"),
        table_name="sources",
    )

    op.drop_index(
        op.f("ix_sources_id"),
        table_name="sources",
    )

    op.drop_table("sources")

    op.drop_index(
        op.f("ix_think_tanks_is_active"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_is_key"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_parent_id"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_country"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_name_en"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_name"),
        table_name="think_tanks",
    )

    op.drop_index(
        op.f("ix_think_tanks_id"),
        table_name="think_tanks",
    )

    op.drop_table("think_tanks")

    bind = op.get_bind()

    postgresql.ENUM(
        name="crawlstatusenum",
    ).drop(bind, checkfirst=True)

    postgresql.ENUM(
        name="sourcetypeenum",
    ).drop(bind, checkfirst=True)

    postgresql.ENUM(
        name="organizationtypeenum",
    ).drop(bind, checkfirst=True)
