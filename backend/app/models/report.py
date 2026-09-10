from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base


class Report(Base):

    __tablename__ = "reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    source_id = Column(
        Integer,
        ForeignKey(
            "sources.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    title = Column(
        String(500),
        nullable=False
    )

    url = Column(
        Text,
        nullable=False
    )

    normalized_url = Column(
        Text
    )

    content_hash = Column(
        String(64),
        index=True
    )

    content = Column(
        Text
    )

    pdf_url = Column(
        Text,
        nullable=True,
    )

    page_count = Column(
        Integer,
        nullable=True,
    )

    non_empty_page_count = Column(
        Integer,
        nullable=True,
    )

    pdf_byte_length = Column(
        Integer,
        nullable=True,
    )

    crawl_status = Column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    content_fetched_at = Column(
        DateTime,
        nullable=True,
    )

    crawl_error = Column(
        Text,
        nullable=True,
    )

    published_at = Column(
        DateTime
    )

    translation = Column(
        Text,
        nullable=True
    )

    summary = Column(
        Text,
        nullable=True
    )

    commentary = Column(
        Text,
        nullable=True
    )

    ai_status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending"
    )

    ai_retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )

    ai_generated_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    source = relationship(
        "Source",
        back_populates="reports"
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "normalized_url",
            name="uq_report_source_url"
        ),
    )
