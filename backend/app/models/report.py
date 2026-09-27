from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.status import ReportAIStatus, ReportCrawlStatus, ReportReviewStatus
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.report_review_event import ReportReviewEvent
    from app.models.source import Source


class Report(Base):
    """已入库的智库研究报告。"""

    __tablename__ = "reports"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "normalized_url",
            name="uq_report_source_url",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    normalized_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
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

    content_kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pdf",
        server_default="pdf",
        index=True,
    )

    crawl_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ReportCrawlStatus.pending.value,
        index=True,
    )

    content_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    crawl_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    translation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 业务含义：分析评论稿第一部分“主要观点”。
    # 字段名保留为 summary，避免引入数据库迁移和历史数据兼容成本。
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 业务含义：分析评论稿第二部分“深层研判”。
    commentary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ReportAIStatus.pending.value,
        server_default=ReportAIStatus.pending.value,
    )

    ai_retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    ai_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ReportReviewStatus.pending_review.value,
        server_default=ReportReviewStatus.pending_review.value,
        index=True,
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="reports",
    )

    review_events: Mapped[list["ReportReviewEvent"]] = relationship(
        "ReportReviewEvent",
        back_populates="report",
        cascade="all, delete-orphan",
    )
