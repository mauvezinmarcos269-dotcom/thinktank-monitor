import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.source import Source


class OrganizationTypeEnum(str, enum.Enum):
    """机构类别。"""

    think_tank = "think_tank"
    research_association = "research_association"
    research_institute = "research_institute"
    foundation = "foundation"
    international_organization = "international_organization"


class ThinkTank(Base):
    """智库、研究所、基金会、科研联合会等机构。"""

    __tablename__ = "think_tanks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    name_en: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    organization_type: Mapped[OrganizationTypeEnum] = mapped_column(
        Enum(
            OrganizationTypeEnum,
            name="organizationtypeenum",
        ),
        nullable=False,
        default=OrganizationTypeEnum.think_tank,
        server_default=text("'think_tank'"),
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "think_tanks.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    is_key: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["ThinkTank | None"] = relationship(
        "ThinkTank",
        remote_side="ThinkTank.id",
        back_populates="children",
    )

    children: Mapped[list["ThinkTank"]] = relationship(
        "ThinkTank",
        back_populates="parent",
    )

    sources: Mapped[list["Source"]] = relationship(
        "Source",
        back_populates="think_tank",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
