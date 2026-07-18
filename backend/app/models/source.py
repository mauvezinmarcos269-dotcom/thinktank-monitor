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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.think_tank import ThinkTank


class SourceTypeEnum(str, enum.Enum):
    """来源类型。"""

    website = "website"
    rss = "rss"
    report_library = "report_library"
    topic_page = "topic_page"


class CrawlStatusEnum(str, enum.Enum):
    """来源最近一次抓取状态。"""

    never = "never"
    running = "running"
    success = "success"
    failed = "failed"


class Source(Base):
    """智库旗下可抓取的内容来源。"""

    __tablename__ = "sources"

    __table_args__ = (
        UniqueConstraint(
            "url",
            name="uq_sources_url",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    think_tank_id: Mapped[int] = mapped_column(
        ForeignKey(
            "think_tanks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_type: Mapped[SourceTypeEnum] = mapped_column(
        Enum(
            SourceTypeEnum,
            name="sourcetypeenum",
        ),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    crawl_frequency_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1440,
        server_default=text("1440"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )

    last_crawl_status: Mapped[CrawlStatusEnum] = mapped_column(
        Enum(
            CrawlStatusEnum,
            name="crawlstatusenum",
        ),
        nullable=False,
        default=CrawlStatusEnum.never,
        server_default=text("'never'"),
    )

    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    think_tank: Mapped["ThinkTank"] = relationship(
    "ThinkTank",
    back_populates="sources",
)


    reports: Mapped[list["Report"]] = relationship(
    "Report",
    back_populates="source",
    cascade="all, delete-orphan",
    passive_deletes=True,
)
