from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CrawlCandidate(Base):
    """抓取阶段发现的候选报告。"""

    __tablename__ = "crawl_candidates"

    __table_args__ = (
        Index("ix_crawl_candidates_run_status", "crawl_run_id", "status"),
        Index("ix_crawl_candidates_source_created", "source_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    crawl_run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "crawl_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    report_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "reports.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    normalized_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="discovered",
        index=True,
    )

    skip_reason_code: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    skip_reason_label: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    relevance: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    relevance_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_china_related: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    pdf_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    non_empty_page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pdf_byte_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    content_kind: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
