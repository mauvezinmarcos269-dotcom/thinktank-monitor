from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.status import CrawlRunStatus
from app.models.base import Base


class CrawlRun(Base):
    """一次来源抓取运行记录。"""

    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=CrawlRunStatus.pending.value,
    )

    found_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    saved_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
