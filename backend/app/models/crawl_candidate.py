from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from .base import Base


class CrawlCandidate(Base):
    __tablename__ = "crawl_candidates"

    id = Column(Integer, primary_key=True, index=True)
    crawl_run_id = Column(
        Integer,
        ForeignKey("crawl_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = Column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id = Column(
        Integer,
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(500), nullable=True)
    url = Column(Text, nullable=False)
    normalized_url = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="discovered", index=True)
    skip_reason_code = Column(String(80), nullable=True, index=True)
    skip_reason_label = Column(String(120), nullable=True)
    error = Column(Text, nullable=True)
    relevance = Column(String(30), nullable=True)
    relevance_reason = Column(Text, nullable=True)
    is_china_related = Column(Boolean, nullable=True)
    pdf_url = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    non_empty_page_count = Column(Integer, nullable=True)
    pdf_byte_length = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_crawl_candidates_run_status", "crawl_run_id", "status"),
        Index("ix_crawl_candidates_source_created", "source_id", "created_at"),
    )
