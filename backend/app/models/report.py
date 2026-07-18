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


    published_at = Column(
        DateTime
    )


    analysis_status = Column(
        String(30),
        default="pending"
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
